# Skyrim no Mac (Apple Silicon) 🏛️

> Projeto de engenharia reversa para fazer **The Elder Scrolls V: Skyrim Special Edition** rodar nativamente em Apple Silicon (M1-M6+) usando Wine + D3DMetal, com método documentado e aberto à comunidade.

## Status Atual

| Componente | Status |
|-----------|--------|
| Boot do jogo | ✅ **FUNCIONANDO** — tela de criação de personagem visível e interativa |
| Gráficos (DX11→Metal) | ✅ MoltenVK + D3DMetal renderizando |
| Controles | ✅ Teclado + Controle Xbox |
| Áudio ambiente/ações/menus | ✅ XAudio2 PCM direto |
| Música (.xwm) | ❌ WMA decoder pendente |
| Vozes (.fuz) | ❌ XMA decoder pendente |
| Saves | ✅ (via Steam no prefixo) |

## Paredes derrubadas (crônica)

| # | Parede | Solução |
|---|--------|---------|
| 1 | Steam handshake | `steam_api64.dll` patch (RestartAppIfNecessary→FALSE) + `SteamAppId=489830` |
| 2 | Gráficos DX11 | Wine Sikarugir 10.0 + D3DMetal v2.1 (Apple) |
| 3 | Crash de áudio | **4 patches binários no SkyrimSE.exe** (JE→JMP — pula calls em pointer inválido) |

## Estrutura

```
├── CHARTER.md          # Missão, fases, regras do método
├── LOG.md              # Diário de bordo — cada experimento documentado
├── .gitignore          # Exclui binários grandes (engines, prefix, GStreamer)
├── run-skyrim.sh       # Lança o jogo direto (SteamAppId + D3DMetal env)
├── run-steam.sh        # Lança o cliente Steam dentro do prefixo
├── run-cx.sh           # Lança com engine CrossOver+DXMT (experimental)
├── tools/
│   ├── patch_steam_api.py     # Patch 3 bytes: RestartAppIfNecessary→FALSE
│   ├── SteamSetup.exe         # Instalador do Steam (baixado)
│   └── auto-run-014.sh        # Automação de testes
└── docs/               # Análises REA (futuro)
```

## Receita da comunidade (o que você precisa)

### Pré-requisitos
- Mac com Apple Silicon (M1/M2/M3/M4/M5/M6)
- macOS 26+ (para D3DMetal)
- Skyrim Special Edition **legítimo** (arquivos do jogo ~15GB)
- Steam account logada

### Engine necessária (não incluída — grande demais pra GitHub)
```
~/Library/Application Support/3Pi2/Engines/wine-sikarugir10.0-d3dmetal2.1/
```
Obtenha do Porting Kit (Wineskin) ou construa do zero. Veja `CHARTER.md` para detalhes.

### Patches necessários
1. **steam_api64.dll**: `tools/patch_steam_api.py`
2. **SkyrimSE.exe**: 4× JE→JMP (offsets: `0x100e5b8`, `0x100e5c6`, `0x100e5f3`, `0x100f290`)

### Variáveis de ambiente
```bash
export WINEPREFIX=<prefix>
export DYLD_FALLBACK_LIBRARY_PATH=<engine>/lib:<engine>/lib/external:<engine>/dylibs
export PATH=<engine>/bin:$PATH
export D3DMETAL_FORCE=1
export MOLTENVKCX=1
export WINEESYNC=1
export WINEMSYNC=1
export SteamAppId=489830
export SteamGameId=489830
```

### Executar
```bash
# 1. Instalar Steam no prefixo (uma vez)
./run-steam.sh setup

# 2. Logar no Steam
./run-steam.sh steam

# 3. Lançar o jogo (com Steam rodando!)
./run-skyrim.sh
```

## Cronologia

### Fase 0 — Ambiente ✅
- Engine Sikarugir+D3DMetal copiada pro SSD
- WINEPREFIX inicializado
- Scripts de execução criados

### Fase 1 — Baseline ✅
- Jogo crasha no Steam handshake (exit 53)
- Descoberta: `SteamAPI_RestartAppIfNecessary` → relança via `steam://`

### Fase 2 — Patch Steam ✅
- Patch 3 bytes no steam_api64.dll
- Jogo passa do handshake mas crasha no áudio
- Descoberta: `SteamAPI_Init` exige Steam de verdade

### Fase 3 — Steam Real ✅
- Steam (Wine) instalado no prefixo, login OK
- Jogo passa handshake, chega aos gráficos
- Vulkan instance criado, MoltenVK ativo

### Fase 4 — Crash de Áudio ✅
- Diagnóstico: WMA decoder MFT retorna pointer inválido
- Root cause: GStreamer não funciona em Rosetta/Wine (scan de plugins falha)
- Solução: 4 patches cirúrgicos no exe (JE→JMP)
- **Resultado: JOGO RODANDO!**

### Fase 5 — Áudio Completo (em andamento)
- Música/vozes pendentes
- Caminho: registrar wmadmod.dll como MFT no registry
- Ou: DLLs nativas Windows Media Format

## Aviso Legal

Este projeto **não distribui** nenhum arquivo do jogo, código proprietário ou assets da Bethesda. O usuário precisa possuir uma cópia legítima do Skyrim Special Edition. Os patches são para interoperabilidade pessoal, não para pirataria.

## Licença

MIT (para o código e documentação deste repositório)

## Créditos

- **Projeto**: CleversonBamberg (idealizador e testador)
- **AI Engineer**: Claude/3Pi2 (análise, patches, documentação)
- **Engines**: Wine (WineHQ), Sikarugir (Kegworks), D3DMetal (Apple GPTK)
- **Inspiração**: Bloodborne PC (Supermedo), Pinyon Shift, CleanMyMac CLI (MacPaw)
