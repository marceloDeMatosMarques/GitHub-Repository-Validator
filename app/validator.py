import base64
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

LICENSE_APPROVED = {"mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause", "gpl-2.0", "gpl-3.0"}
LICENSE_CONDITIONAL = {"lgpl-2.1", "lgpl-3.0"}
LICENSE_RESTRICTIVE = {"agpl-3.0"}

README_SECTIONS = ["installation", "usage", "examples", "license", "contributing"]

BADGE_PATTERNS = [
    r"!\[[^\]]*\]\([^\)]*badge[^\)]*\)",
    r"\[!\[[^\]]*\]\([^\)]*badge[^\)]*\)\]",
]


class GitHubRepoValidator:
    def __init__(self, token: Optional[str] = None, base_url: str = "https://api.github.com"):
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "github-repo-validator",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.base_url = base_url
        self.headers = headers
        self.client = httpx.AsyncClient(headers=self.headers, timeout=20.0)

    async def close(self) -> None:
        await self.client.aclose()

    def _normalize_repo(self, repo: str) -> Tuple[str, str]:
        parts = repo.strip().lower().split("/")
        if len(parts) != 2 or not all(parts):
            logger.warning(f"Formato de repositório inválido: {repo}")
            raise ValueError("Repositório inválido. Use o formato owner/repo.")
        logger.debug(f"Repositório normalizado: {parts[0]}/{parts[1]}")
        return parts[0], parts[1]

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        logger.debug(f"Requisição à API GitHub: {url}")
        response = await self.client.get(url, params=params)
        if response.status_code == 404:
            logger.warning(f"Repositório não encontrado: {url}")
            raise HTTPException(status_code=404, detail="Repositório não encontrado.")
        if response.status_code == 403:
            detail = "Acesso à API do GitHub negado."
            try:
                payload = response.json()
                detail = payload.get("message", detail)
            except ValueError:
                detail = response.text or detail
            if "rate limit exceeded" in detail.lower() or response.headers.get("X-RateLimit-Remaining") == "0":
                logger.error(f"GitHub rate limit excedido: {detail}")
                raise HTTPException(
                    status_code=429,
                    detail=(
                        "GitHub rate limit exceeded. Configure a variável de ambiente "
                        "GITHUB_TOKEN para aumentar o limite e tente novamente."
                    ),
                )
            logger.warning(f"Permissão negada na API: {detail}")
            raise HTTPException(status_code=403, detail=f"Permissão negada na API do GitHub: {detail}")
        response.raise_for_status()
        return response.json()

    async def _get_text_file(self, path: str) -> Optional[str]:
        try:
            content = await self._get(path)
            if isinstance(content, dict) and content.get("encoding") == "base64":
                return base64.b64decode(content["content"]).decode("utf-8", errors="ignore")
        except HTTPException:
            return None
        return None

    async def validate(self, repo: str) -> Dict[str, Any]:
        owner, name = self._normalize_repo(repo)
        repo_data = await self._get(f"/repos/{owner}/{name}")
        readme_text = await self._get_text_file(f"/repos/{owner}/{name}/readme")
        release_data = await self._get(f"/repos/{owner}/{name}/releases", params={"per_page": 10})
        branches = await self._get(f"/repos/{owner}/{name}/branches", params={"per_page": 100})
        contributors = await self._get(f"/repos/{owner}/{name}/contributors", params={"per_page": 100})
        issues_open = await self._get(f"/search/issues", params={"q": f"repo:{owner}/{name} type:issue state:open"})
        issues_closed = await self._get(f"/search/issues", params={"q": f"repo:{owner}/{name} type:issue state:closed"})
        pulls_closed = await self._get(f"/repos/{owner}/{name}/pulls", params={"state": "closed", "per_page": 100})
        pulls_open = await self._get(f"/repos/{owner}/{name}/pulls", params={"state": "open", "per_page": 100})

        contents = await self._get(f"/repos/{owner}/{name}/contents", params={"per_page": 100})
        docs_exists = await self._exists_path(owner, name, "docs")
        examples_exists = await self._exists_path(owner, name, "examples")
        changelog_exists = await self._exists_path(owner, name, "CHANGELOG.md")
        contributing_exists = await self._exists_path(owner, name, "CONTRIBUTING.md")
        conduct_exists = await self._exists_path(owner, name, "CODE_OF_CONDUCT.md")
        security_exists = (
            await self._exists_path(owner, name, "SECURITY.md") or
            await self._exists_path(owner, name, ".github/SECURITY.md")
        )
        github_workflows = await self._exists_path(owner, name, ".github/workflows")

        last_commit_info = await self._get_commits(owner, name)

        activity_report = self._evaluate_activity(
            repo_data,
            release_data,
            branches,
            contributors,
            last_commit_info,
        )
        popularity_report = self._evaluate_popularity(repo_data)
        documentation_report = self._evaluate_documentation(readme_text, docs_exists, examples_exists, changelog_exists)
        license_report = self._evaluate_license(repo_data)
        tests_ci_report = self._evaluate_tests_ci(readme_text, github_workflows)
        community_report = self._evaluate_community(issues_open, issues_closed, pulls_closed, pulls_open, contributing_exists, conduct_exists)
        security_report = self._evaluate_security(security_exists, repo_data)

        score = sum([
            activity_report["score"],
            popularity_report["score"],
            documentation_report["score"],
            license_report["score"],
            tests_ci_report["score"],
            community_report["score"],
            security_report["score"],
        ])

        elimination_reason = self._check_elimination(
            repo_data,
            last_commit_info,
            license_report,
            security_report,
        )

        verdict = self._build_verdict(score, elimination_reason, activity_report)

        return {
            "repository": f"{owner}/{name}",
            "verdict": verdict,
            "score": score,
            "elimination_reason": elimination_reason,
            "details": {
                "activity": activity_report,
                "popularity": popularity_report,
                "documentation": documentation_report,
                "license": license_report,
                "tests_ci": tests_ci_report,
                "community": community_report,
                "security": security_report,
            },
        }

    async def _exists_path(self, owner: str, name: str, path: str) -> bool:
        try:
            await self._get(f"/repos/{owner}/{name}/contents/{path}")
            return True
        except HTTPException:
            return False

    async def _get_commits(self, owner: str, name: str) -> Dict[str, Any]:
        since_90 = datetime.now(timezone.utc) - timedelta(days=90)
        commits = await self._get(f"/repos/{owner}/{name}/commits", params={"since": since_90.isoformat(), "per_page": 100})
        last_commit = commits[0] if commits else None
        return {
            "list": commits,
            "last_commit_date": self._parse_date(last_commit["commit"]["committer"]["date"]) if last_commit else None,
        }

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _evaluate_activity(
        self,
        repo_data: Dict[str, Any],
        release_data: List[Dict[str, Any]],
        branches: List[Dict[str, Any]],
        contributors: List[Dict[str, Any]],
        commit_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        last_commit = commit_info["last_commit_date"]
        days_since_commit = None if not last_commit else (now - last_commit).days
        release_recent = any(
            self._parse_date(release.get("published_at")) and now - self._parse_date(release.get("published_at")) <= timedelta(days=90)
            for release in release_data
        )
        active_contributors = sum(
            1 for contributor in contributors if contributor.get("contributions", 0) >= 5
        )
        protected_branch = any(branch.get("protected") for branch in branches)
        commit_rate = len(commit_info["list"])

        score = 0
        notes: List[str] = []
        if last_commit and days_since_commit <= 30:
            score += 10
        else:
            notes.append("Último commit não está dentro de 30 dias")

        if commit_rate >= 3:
            score += 5
        else:
            notes.append("Baixa frequência de commits recentes")

        if release_recent:
            score += 5
        else:
            notes.append("Nenhum release publicado nos últimos 3 meses")

        if active_contributors >= 3:
            score += 3
        else:
            notes.append("Menos de 3 contribuidores ativos no último trimestre")

        if protected_branch:
            score += 2
        else:
            notes.append("Branch principal não está protegida ou não foi identificado branch protegido")

        return {
            "score": score,
            "last_commit_days": days_since_commit,
            "commits_last_90_days": commit_rate,
            "release_recent": release_recent,
            "active_contributors": active_contributors,
            "protected_branch": protected_branch,
            "notes": notes,
        }

    def _evaluate_popularity(self, repo_data: Dict[str, Any]) -> Dict[str, Any]:
        stars = repo_data.get("stargazers_count", 0)
        forks = repo_data.get("forks_count", 0)
        watchers = repo_data.get("subscribers_count", 0)
        score = 0
        notes: List[str] = []

        if stars >= 10000:
            score += 5
        else:
            notes.append("Stars abaixo de 10.000")

        if forks >= max(1, stars // 10):
            score += 3
        else:
            notes.append("Razão forks/stars abaixo de 1:10")

        if watchers >= max(1, stars // 100):
            score += 2
        else:
            notes.append("Watchers abaixo de 1% das stars")

        return {
            "score": score,
            "stars": stars,
            "forks": forks,
            "watchers": watchers,
            "notes": notes,
        }

    def _evaluate_documentation(
        self,
        readme_text: Optional[str],
        docs_exists: bool,
        examples_exists: bool,
        changelog_exists: bool,
    ) -> Dict[str, Any]:
        score = 0
        notes: List[str] = []

        if readme_text:
            present_sections = [section for section in README_SECTIONS if re.search(rf"\\b{section}\\b", readme_text, re.IGNORECASE)]
            if len(present_sections) >= 4:
                score += 7
            else:
                notes.append("README não contém seções suficientes: descrição, instalação, uso e exemplos")
            if any(re.search(pattern, readme_text, re.IGNORECASE) for pattern in BADGE_PATTERNS):
                score += 2
            else:
                notes.append("README não contém badges visíveis")
        else:
            notes.append("README não foi encontrado")

        if docs_exists:
            score += 3
        else:
            notes.append("Pasta docs ou documentação externa não encontrada")

        if examples_exists:
            score += 2
        else:
            notes.append("Pasta examples ou demo funcional não encontrada")

        if changelog_exists:
            score += 1
        else:
            notes.append("CHANGELOG.md não encontrado")

        return {
            "score": score,
            "readme_found": bool(readme_text),
            "docs_exists": docs_exists,
            "examples_exists": examples_exists,
            "changelog_exists": changelog_exists,
            "notes": notes,
        }

    def _evaluate_license(self, repo_data: Dict[str, Any]) -> Dict[str, Any]:
        license_info = repo_data.get("license") or {}
        license_key = (license_info.get("key") or "").lower()
        score = 0
        notes: List[str] = []

        if license_key in LICENSE_APPROVED:
            score += 15
        elif license_key in LICENSE_CONDITIONAL:
            score += 7
            notes.append("Licença condicional: exige atenção ao uso e integração")
        elif license_key in LICENSE_RESTRICTIVE:
            score += 2
            notes.append("Licença AGPL: pode ser restritiva em serviços SaaS")
        elif license_key:
            notes.append(f"Licença detectada: {license_key}")
        else:
            notes.append("Licença ausente")

        return {
            "score": score,
            "license_key": license_key,
            "license_name": license_info.get("name"),
            "notes": notes,
        }

    def _evaluate_tests_ci(self, readme_text: Optional[str], github_workflows: bool) -> Dict[str, Any]:
        score = 0
        notes: List[str] = []

        if github_workflows:
            score += 5
        else:
            notes.append("GitHub Actions não configurado em .github/workflows")

        if readme_text and any(re.search(pattern, readme_text, re.IGNORECASE) for pattern in BADGE_PATTERNS):
            score += 3
        else:
            notes.append("Nenhum badge de build/teste detectado no README")

        if readme_text and re.search(r"coverage|cobertura|teste[s]?", readme_text, re.IGNORECASE):
            score += 2
        else:
            notes.append("Nenhuma menção clara a cobertura de testes no README")

        return {
            "score": score,
            "github_actions": github_workflows,
            "notes": notes,
        }

    def _evaluate_community(
        self,
        issues_open: Dict[str, Any],
        issues_closed: Dict[str, Any],
        pulls_closed: List[Dict[str, Any]],
        pulls_open: List[Dict[str, Any]],
        contributing_exists: bool,
        conduct_exists: bool,
    ) -> Dict[str, Any]:
        score = 0
        notes: List[str] = []
        open_count = issues_open.get("total_count", 0)
        closed_count = issues_closed.get("total_count", 0)
        total_issues = open_count + closed_count
        issue_response = None

        if total_issues > 0:
            closed_rate = closed_count / total_issues
            if closed_rate >= 0.6:
                score += 3
            else:
                notes.append("Taxa de fechamento de issues abaixo de 60%")
        else:
            notes.append("Não há issues suficientes para avaliar a comunidade")

        pull_merged = sum(1 for pr in pulls_closed if pr.get("merged_at"))
        if pull_merged >= 1:
            score += 3
        else:
            notes.append("Nenhum PR externo mergeado recentemente")

        if contributing_exists:
            score += 2
        else:
            notes.append("CONTRIBUTING.md ausente")

        if conduct_exists:
            score += 2
        else:
            notes.append("CODE_OF_CONDUCT.md ausente")

        return {
            "score": score,
            "issues_open": open_count,
            "issues_closed": closed_count,
            "pulls_open": len(pulls_open),
            "pulls_merged_recent": pull_merged,
            "contributing_exists": contributing_exists,
            "conduct_exists": conduct_exists,
            "notes": notes,
        }

    def _evaluate_security(self, security_exists: bool, repo_data: Dict[str, Any]) -> Dict[str, Any]:
        score = 0
        notes: List[str] = []

        if security_exists:
            score += 5
        else:
            notes.append("SECURITY.md ausente")

        if repo_data.get("has_issues"):
            score += 5
        else:
            notes.append("Repositório não está configurado para issues")

        if repo_data.get("archived"):
            notes.append("Repositório arquivado")
        else:
            score += 5

        return {
            "score": score,
            "security_policy_exists": security_exists,
            "archived": repo_data.get("archived", False),
            "notes": notes,
        }

    def _check_elimination(
        self,
        repo_data: Dict[str, Any],
        last_commit_info: Dict[str, Any],
        license_report: Dict[str, Any],
        security_report: Dict[str, Any],
    ) -> Optional[str]:
        last_commit = last_commit_info["last_commit_date"]
        now = datetime.now(timezone.utc)
        if last_commit and (now - last_commit) > timedelta(days=365):
            return "Último commit há mais de 1 ano"
        if not license_report["license_key"]:
            return "Sem licença definida"
        if repo_data.get("archived"):
            return "Repositório arquivado"
        if security_report["security_policy_exists"] is False:
            return "Sem política de segurança definida"
        return None

    def _build_verdict(self, score: int, elimination_reason: Optional[str], activity_report: Dict[str, Any]) -> str:
        if elimination_reason:
            return "Reprovado"
        if score >= 80:
            return "Aprovado"
        if score >= 60:
            return "Condicional"
        return "Reprovado"
