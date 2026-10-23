# 🏛️ Projeto Skyrim no Mac (macOS 27+)

**Missão:** fazer The Elder Scrolls V: Skyrim Special Edition rodar nativamente em Apple Silicon (macOS 27+), com método documentado e aberto à comunidade.

**Método:** Engenharia reversa assistida (REA + Ghidra) sobre `SkyrimSE.exe` + camada de compatibilidade Wine/D3DMetal. Nível 1 evolutivo — se as evidências mostrarem caminho, sobe pra recompilação estática (Nível 2).

**Não temos pressa.** Cada experimento fica documentado. Cada crash é uma pista.

---

## Fases

| Fase | Objetivo | Entregável |
|------|----------|------------|
| **0 — Ambiente** ✅ | Engine + prefix + scripts no SSD | Este repositório |
| **1 — Baseline** | Rodar o exe e capturar o crash nº 1 | `logs/baseline-001.log` |
| **2 — REA** | Análise do binário: imports, D3D11, caminho de inicialização | `docs/rea-*.md` |
| **3 — Hipóteses** | Fix por fix: d3dcompiler_47, overrides, launcher bypass | `LOG.md` com cada teste |
| **4 — Estabilidade** | Gameplay estável + performance (ESYNC/MSYNC, tuning D3DMetal) | Guia de jogo |
| **5 — Comunidade** | Empacotar: preset 3Pi2 + guia + tudo aberto | Release público |

## Regras do projeto

1. **Nada de palpite sem evidência** — cada mudança nasce de um log
2. **Um experimento por vez** — variável isolada
3. **Tudo versionado aqui no SSD** — logs brutos em `logs/`, decisões em `LOG.md`
4. **O jogo é do usuário** — nós distribuímos só código e conhecimento (padrão Bloodborne PC)

## Contexto técnico conhecido

- `SkyrimSE.exe`: PE32+ x86-64, Direct3D 11 (high-level — tradução D3DMetal cobre)
- Sem SKSE, sem mods (vanilla = superfíce mínima de ataque ao problema)
- **Sem DRM Steam no exe** (famoso: roda direto; `steam_api64.dll` é opcional)
- Exigência documentada: `d3dcompiler_47.dll` (hipótese #1 do crash)
- Launcher (`SkyrimSELauncher.exe`) problemático no Wine — rodar o exe direto
