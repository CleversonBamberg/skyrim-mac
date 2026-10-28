# 🛠️ Instalação do zero (após formatar o Mac)

Este guia é o passo a passo quando você **apagou/reinstalou o macOS** e quer reconstruir tudo do zero usando o projeto `skyrim-mac` que está no SSD externo (`/Volumes/SSD120GB/skyrim-mac`).

## O que já está no SSD externo (não precisa baixar novamente)

| O que | Onde |
|-------|------|
| Projeto + scripts + instalador | `/Volumes/SSD120GB/skyrim-mac/` |
| Baixa de instalação (zip) | `dist/skyrim-mac-v1.0.zip` |
| Engine Wine+D3DMetal (3Pi2 + Sikarugir) | `mods/engines-3pi2-backup/` |
| Tradução PT-BR (extraída) | `mods/traducao-58406/` |
| CHARTER / LOG / README | raiz do projeto |

## O que você precisará baixar novamente após a formatação

| Item | Fonte | Observação |
|------|-------|------------|
| Skyrim Special Edition | Steam (Biblioteca) | Login na sua conta Steam |
| Steam (Windows via Wine) | Baixa automaticamente via `INSTALAR.command` | O assistente baixa o `SteamSetup.exe` da Valve |
| Engine Wine+D3DMetal | Já está em `mods/engines-3pi2-backup/` | Se quiser a mais recente: baixe o 3Pi2 novamente |
| Dublagem PT-BR (opcional) | Nexus Mods #105861 | Só se quiser vozes em português |

---

## Passo a passo pós-formatação

### 1. Recupere o projeto (já está no SSD externo)
Não precisa clonar nada — o projeto já está em `/Volumes/SSD120GB/skyrim-mac/`.

### 2. Recupere a engine Wine+D3DMetal
O 3Pi2 está em `mods/engines-3pi2-backup/`. Você pode:
- **Opção A (rápida):** copiar de volta para `~/Library/Application Support/3Pi2/Engines/` e o instalador acha sozinho
- **Opção B:** apontar no instalador com `ENGINE_DIR="/Volumes/SSD120GB/skyrim-mac/mods/engines-3pi2-backup/wine-sikarugir10.0-d3dmetal2.1" ./INSTALAR.command`

### 3. Rodar o instalador
```bash
cd /Volumes/SSD120GB/skyrim-mac
duplo-clique em INSTALAR.command
```
Ou via Terminal:
```bash
./INSTALAR.command
```

O assistente vai:
1. Checar Apple Silicon + Python
2. Linkar a engine Wine+D3DMetal
3. Criar o prefixo Wine
4. Baixar e instalar o Steam (da Valve)
5. Esperar você logar no Steam e instalar o Skyrim pela Biblioteca
6. Detectar dublagem/tradução na pasta (se houver .7z)
7. Rodar `instalar-mac.sh` (patches + vozes + música + legendas)
8. Criar o atalho `Skyrim.command` na Mesa

### 4. Jogar
Duplo-clique em **Skyrim.command** na Mesa → Steam sobe sozinho → jogo lança.

---

## Áudio: escolha na instalação

O instalador pergunta (se achar a dublagem .7z):
- **S** = dublagem PT-BR (67 mil falas stereo) + inglês nas não-dubladas
- **n** = vozes originais em inglês (75.408 falas, idêntico ao Windows) + legendas PT-BR

Trocar depois de instalado:
- original → dublada: `PTBR="/caminho/da/dublagem.7z" ./instalar-mac.sh`
- dublada → original: `python3 tools/voz_nativa_lotes.py`

---

## Como baixar a dublagem PT-BR (opcional)

Se quiser vozes em português, baixe antes de rodar o instalador:
- **Nexus Mods #105861** — "Skyrim - PT-BR Voice Dubbing" (ou similar)
- Coloque o `.7z` na mesma pasta do `INSTALAR.command`

---

## Arquivos do projeto (referência rápida)

```
skyrim-mac/
├── INSTALAR.command          # assistente de instalação (duplo-clique)
├── instalar-mac.sh           # script de instalação detalhado
├── tools/
│   ├── fuz_xwma_to_pcm.py    # conversor xWMA → PCM
│   ├── bsa_extract.py        # extrator BSA v105
│   ├── patch_skyrimse_exe.py # patch anti-crash do áudio
│   ├── patch_steam_api.py    # patch do Steam handshake
│   └── voz_nativa_lotes.py   # conversor lotes de vozes originais
├── mods/
│   ├── traducao-58406/       # tradução PT-BR (extraída)
│   └── engines-3pi2-backup/  # engine Wine+D3DMetal (backup)
├── docs/
│   ├── nexus-page.md         # texto da página do Nexus
│   └── screenshots/          # capturas de tela
├── CHARTER.md                # missão do projeto
├── LOG.md                    # 50 runs documentadas
└── README.md                 # receita completa da comunidade
```

---

**Precisa de ajuda?** Abra uma issue no GitHub: https://github.com/CleversonBamberg/skyrim-mac
