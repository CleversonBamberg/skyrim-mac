# 📓 LOG.md — Diário de bordo do projeto skyrim-mac

Cada experimento: uma variável por vez, evidência no log bruto (`logs/`).

---

## #001 — Baseline (2026-10-21)

**Setup:** engine Sikarugir 10.0 D3DMetal (cópia própria em `engine/`), prefix recém-inicializado, `SkyrimSE.exe` direto (sem launcher), WINEDEBUG=+err,+seh,+loaddll,+file.

**Resultado: EXIT 53 — jogo nunca chegou aos gráficos.**

**Evidência (`logs/baseline-001.log`, 146.889 linhas):**
- `SkyrimSE.exe` carregou como native em 0x140000000 ✓
- DLLs de sistema carregaram normais (user32, uxtheme, concrt140 builtin…) ✓
- `d3dcompiler_47.dll` **existe** no prefix (probes de d3dcompiler_33/34/35 ausentes são só enumeração normal)
- Morte: busca `appmanifest_489830.acf` → tenta `steam://run/489830` → **não há Steam** → exit 53

**Diagnóstico:** `SteamAPI_RestartAppIfNecessary(489830)` retornou true → o jogo tenta se relançar via protocolo Steam e sai. Este é o bloqueio clássico que faz "Skyrim não roda em Wine nenhum" quando lançado fora do Steam.

**Decisão:** #002 testa a PRÓXIMA variável (gráficos/D3D11) sem instalar Steam — patch cirúrgico no `steam_api64.dll` do usuário (backup preservado): `SteamAPI_RestartAppIfNecessary` → `xor eax,eax; ret` (retorna false = "já estou no Steam"). Modo diagnóstico; a receita final da comunidade usará Steam real.

---

## #002 — Patch steam_api (diagnóstico de gráficos) — em andamento

## #002 — Patch steam_api RestartAppIfNecessary (2026-10-21)

**Patch:** `SteamAPI_RestartAppIfNecessary` → `xor eax,eax; ret` (tools/patch_steam_api.py, backup .orig).
**Resultado:** o jogo PASSOU do relançamento — carregou `steam_api64` (native), `bink2w64`, `d3d11`+`dxgi` builtin e **MoltenVK inicializou** (Vulkan→Metal vivo). Morre logo depois, exit 53.

## #003 — Captura das últimas palavras (+debugstr) (2026-10-21)

**Evidência (`logs/run-003-debugstr.log`):**
```
[S_API] SteamAPI_Init(): SteamAPI_IsSteamRunning() did not locate a running instance of Steam.
[S_API] SteamAPI_Init(): Could not determine Steam client install directory.
```
→ exit 53 (erro Windows 53 = "network path not found" = Steam ausente).

**Diagnóstico:** este build exige `SteamAPI_Init` bem-sucedido — o jogo não tolera Steam ausente. A rota do patch única não basta.

**Decisão:** instalar o **cliente Steam real no prefixo do projeto** (recipe validada do 3Pi2). Próximo experimento (#004) = primeiro com Steam real → isola de vez a variável gráfica (D3D11/D3DMetal).

## Preparação #004
- Jogo movido para `SteamLibrary/steamapps/common/Skyrim Special Edition` (biblioteca padrão do Steam)
- SteamSetup.exe baixado (tools/)
- A lançar com WINEDEBUG herdado: quando o jogo for iniciado DO Steam, capturamos o log pela herança de ambiente

## #004 — Primeira via Steam real (2026-10-21)

**Setup:** Steam (Wine) instalado no prefixo, login OK, jogo instalado, lançado via `-applaunch 489830`.
**Resultado:** SteamAPI satisfeito ("steamclient64.dll OK"), launcher do jogo abriu janela (user viu), engine criou threads (WINE_NAME_THREAD), carregou d3d11/dxgi/bink, MoltenVK inicializou — e o jogo saiu silenciosamente. Criou `My Games/Skyrim Special Edition/Skyrim*.ini` (boot interno avançado!).

## #005 — tentativa de telemetria +dxgi/+d3d11

**Descoberta:** os canais +dxgi/+d3d11 do Sikarugir são MUDOS (implementação CX não emite trace). Steam morreu no processo com assert interno (pipes.cpp — efeito dos force-kills repetidos).

## #006 — MoltenVK trace total (2026-10-22) ⭐

**Setup:** MVK_CONFIG_TRACE_VULKAN_CALLS=1 + MVK_CONFIG_LOG_LEVEL=debug +debugstr.
**Evidência decisiva:**
- Launcher (`SkyrimSELauncher.exe`) roda PERFEITO — cria VkInstance+VkDevice, UI renderiza (MoltenVK ok), escreve SkyrimPrefs.ini sanas (1366x768 fullscreen)
- Steam vê a GPU: "Apple M6", vram 16GB, driver MoltenVK
- **Jogo real (`SkyrimSE.exe`): enumera a GPU 62 vezes (vkEnumeratePhysicalDevices→Props→MemProps em loop) e NUNCA chama vkCreateDevice** → sai em silêncio
**Diagnóstico:** a camada DXGI/D3D11 do Sikarugir (winemetal) falha dentro de D3D11CreateDevice (antes do VkDevice) de forma silenciosa — o jogo tenta variações 62× e desiste. Sem diagnóstico disponível nessa engine.

**Decisão:** #007 troca de engine → CX26.3+DXMT (família DXVK) que tem log próprio (DXMT_LOG_LEVEL) → vamos capturar QUAL chamada D3D11 do jogo falha.

## #007 — engine CX26.3+DXMT — em andamento

# ═══════════════════════════════════════════════════════════════
# 🏆 22/10/2026, ~21:00 — SKYRIM SE RODANDO NO MAC! 🏆
# ═══════════════════════════════════════════════════════════════
# Tela de criação de personagem VISÍVEL e INTERATIVA.
# CPU ~100%, engine 3D renderizando via D3DMetal → Metal.
#
# ═══ RECEITA COMPLETA (para comunidade) ═══
#
# Paredes derrubadas, em ordem:
#
# 1. STEAM HANDSHAKE
#    - Steam (Wine) instalado no prefixo, logado
#    - steam_api64.dll patchado: RestartAppIfNecessary → xor eax,eax; ret
#    - SteamAppId=489830 SteamGameId=489830 no env
#
# 2. GRÁFICOS (D3DMetal)
#    - Engine: Wine Sikarugir 10.0 + D3DMetal v2.1
#    - D3DMETAL_FORCE=1 MOLTENVKCX=1 (ativam o backend Metal)
#    - MoltenVK inicializa, VkInstance criado, d3d11/dxgi builtin
#
# 3. ÁUDIO (patch cirúrgico no SkyrimSE.exe!)
#    - PROBLEMA: jogo tenta criar decoder WMA via Media Foundation
#      → GStreamer não consegue escanear plugins dentro do Rosetta/Wine
#      → decoder retorna NULL → jogo dereferencia pointer inválido → c0000005
#    - SOLUÇÃO: 4 patches binários no SkyrimSE.exe:
#      Padrão: "TEST RCX,RCX; JE +6; MOV RAX,[RCX]; CALL [RAX+0x10]"
#      → o TEST passa (pointer não é null, é GARBAGE 0xF000000000000010)
#      → o JE não pula (pointer não-zero!)
#      → MOV RAX,[RCX] crasha
#      Patch: JE (0x74) → JMP (0xEB) — SEMPRE pula o call
#      Offsets: 0x100e5b8, 0x100e5c6, 0x100e5f3, 0x100f290 (file offsets)
#      Resultado: jogo SEM ÁUDIO mas SEM CRASH
#
# ═══ VARIÁVEIS DE AMBIENTE (run-skyrim.sh) ═══
# export WINEPREFIX=<prefix>
# export DYLD_FALLBACK_LIBRARY_PATH=<engine>/lib:<engine>/lib/external:<engine>/dylibs
# export PATH=<engine>/bin:$PATH
# export D3DMETAL_FORCE=1
# export MOLTENVKCX=1
# export WINEESYNC=1
# export WINEMSYNC=1
# export SteamAppId=489830
# export SteamGameId=489830
# export WINEDEBUG="+err,+seh,+debugstr"  # opcional, para debug
#
# ═══ PRÓXIMOS PASSOS ═══
# - [ ] Restaurar áudio: instalar DLLs nativas Windows WMA (wmfdist) no prefixo
# - [ ] Testar performance/framerate
# - [ ] Testar salvamento
# - [ ] Empacotar como preset no 3Pi2
# - [ ] Guia da comunidade
#
# ═══════════════════════════════════════════════════════════════

## #030-031 — Patches no áudio (2026-10-22)

**Patch aplicado:** 4 instâncias de `JE +6` → `JMP +6` no SkyrimSE.exe (padrão: TEST RCX; JE; MOV RAX,[RCX]; CALL [RAX+0x10])
**Resultado:** JOGO RODANDO. Tela de criação de personagem visível e interativa. Sem áudio (mudo), mas funcional.
**Backup:** SkyrimSE.exe.pre-audio-patch

## ESTADO PÓS-JOGO (22/10/2026 ~21:30)

**CONFRIMADO PELO USUÁRIO:**
- ✅ Jogo FUNCIONANDO perfeitamente
- ✅ Controles respondem (teclado + controle Xbox)
- ✅ Áudio AMBIENTE funciona
- ✅ Áudio de AÇÕES funciona
- ✅ Áudio de MENUS funciona
- ❌ Vozes/diálogos ausentes (.fuz → XMA)
- ❌ Música ausente (.xwm → WMA)

**CONCLUSÃO:** Os patches cirúrgicos no exe só silenciaram as chamadas MF/GStreamer
que crashavam. O XAudio2 base (PCM direto) funciona sem Media Foundation!
O próximo passo é restaurar o exe e prover DLLs nativas Windows para WMA/XMA.

## Fase 5 — Áudio (23/10/2026)

### Diagnóstico completo
- Wine's Unix-side loader NÃO carrega dylibs externas via Rosetta (nem com paths absolutos)
- GStreamer não inicializa dentro do processo Wine (lsof = zero dylibs carregadas)
- wmadmod.dll builtin é um STUB (131KB, sem decoder real)
- Sons do BSA: todos PCM .wav (5929 arquivos) — funcionam via XAudio2
- Músicas .xwm: comprimidas com LZ4 dentro do BSA, não extraíveis com parser atual
- Vozes .fuz: no Voices_en0.bsa (75408 arquivos), formato XMA

### BREAKTHROUGH: decodificação no macOS
- GStreamer framework tem: avdec_xma1, avdec_xma2 (VOZES!), avdec_wmav2 (MÚSICA!)
- Pipeline: extrair .fuz do BSA → decodificar XMA no macOS → repackear .fuz com PCM
- O jogo toca PCM via XAudio2 (que já funciona!)

### Ferramenta criada
- tools/fuz_convert.py — parser .fuz + decodificador XMA→PCM + repacker
- Aguardando download do mod PT-BR (Nexus 105861) pra testar em lote

### Mod encontrado
- Dublagem Skyrim PT-BR (DovahBR, 6.8k endorsements)
- USA .fuz (mesmo formato vanilla) — MAS o nosso conversor resolve!
- Música não incluída ("Songs still in the original language")

# 🎵 BREAKTHROUGH: MÚSICA FUNCIONANDO! (23/10/2026, 12:00)

## O que aconteceu:
- 263 músicas .xwm do mod "SSE High Quality Music" extraídas
- Convertidas .xwm → .wav PCM usando GStreamer NO MACOS (fora do Wine!)
- Instaladas em Data/music/ como loose files (.wav)
- O jogo ENCONTROU os .wav e tocou via XAudio2 DIRETO!
- SEM decoder WMA! O XAudio2 PCM já funciona!

## Por que música funciona mas vozes não:
- MÚSICA: o jogo procura .xwm mas TAMBÉM aceita .wav loose files
- VOZES: o jogo SEMPRE usa o decoder XMA pra .fuz, sem fallback PCM
- Resultado: música OK, vozes ainda silenciosas

## Converção das vozes PT-BR:
- 67839 .fuz files do mod Dublagem PT-BR (DovahBR) extraídos
- Repackeados com PCM WAV silencioso (lip sync preservado)
- Instalados em Data/sound/voice/
- Vozes silenciosas mas o jogo NÃO CRASHA com elas instaladas

## Ferramenta criada:
- tools/fuz_pcm_repack.py — repackea .fuz substituindo XMA por PCM
- Suporta FUZC e FUZE formats
- 67839 arquivos processados com ZERO falhas

---

## RUN 42 — 2026-10-23: 🔥 BREAKTHROUGH — FORMATO FUZ REAL DESCOBERTO + CONVERSÃO FUNCIONANDO

### O mistério das vozes mudas — RESOLVIDO

Depois de 41 runs tentando decodificar "XMA cru" dos .fuz, descobrimos que **o parser
do formato FUZ estava errado o tempo todo**. O layout real (confirmado em 8000/8000
arquivos do mod PT-BR e 20/20 no Voices_en0.bsa vanilla):

```
offset 0:  "FUZE"
offset 4:  u32 version (1)
offset 8:  u32 LIP SIZE        ← estávamos chamando de "audio_size"
offset 12: LIP sync data       ← estávamos chamando de "audio" (e tentando decodificar como XMA!)
offset 12+lipSize: RIFF....XWMA  ← O SOM É UM RIFF COMPLETO EMBUTIDO NO FINAL
```

- O som embutido é **xWMA = WMA v2 (fmt tag 0x0161), 44100Hz stereo**
- O que extraíamos como "XMA cru" era **LIP sync data** — por isso nenhum decoder funcionava!
- Tamanho exato fecha em 100% dos arquivos: `12 + lipSize + 8 + riffSize == fileSize`

### Por que as vozes eram mudas no Wine

O jogo precisa do decoder **WMA da Microsoft** (`wmadmod.dll`) — que é um **stub no Wine**.
Agora fica claro o porquê: o som dos .fuz é WMA, não XMA. O jogo extrai o RIFF/xWMA,
joga pro decoder WMA (stub) → silêncio.

### A solução (funcionando!)

`tools/fuz_xwma_to_pcm.py`:
1. Parse layout correto: lipSize + LIP + RIFF embutido
2. Decodifica o xWMA com ffmpeg (decoder WMA v2 nativo, embutido no pip imageio-ffmpeg)
3. Remonta: `[FUZE][1][lipSize][LIP][RIFF/WAVE PCM 16-bit]`
   - PCM toca via XAudio2 direto — sem decoder WMA necessário!
   - LIP sync original mantido intacto

### Resultados

- fethis (Dragonborn): 38032B xWMA → **811086B PCM, áudio real confirmado**
- 809 falas do MQ101 (intro) convertidas: **809 ok, 0 erros**
- Instaladas em Data/sound/voice/ (substituindo os repacks antigos bugados)
- Envelope de áudio validado: voz com pausas, picos, ~30s de fala (Elenwen MQ101)

### Caminho do decode (para documentar o esforço)

1. ffmpeg `xma2` decoder exigia extradata de 34 bytes (XMA2WAVEFORMATEX) — descoberto
   lendo `wmaprodec.c` (o decoder XMA mora em wmaprodec.c, não em xmadec.c!)
2. "XMA" decodificava só lixo parcial (~960 samples) — porque era LIP data, não áudio!
3. Teste xWMA via `-f xwma` falhou — o conteúdo real era outra coisa (LIP)
4. Referências-chave: ThyWoof/NswSseSnd (C++ que faz unfuz de SSE: revelou o layout
   LIP-primeiro + RIFF-depois), suglasp/pwsh_convert_fuz_to_xwm (PowerShell, mesmo layout)
5. Confirmação forense: scan dos 67k do mod (8000/8000 layout B) + mmap no BSA vanilla (20/20)

### Pendências

- [ ] TESTE NO JOGO: intro (novo jogo) deve falar PT-BR agora
- [ ] Batch completo 67.839 arquivos → 22050Hz mono (~8.7GB; só há 17GB livres no SSD)
- [ ] Rollback dos .fuz bugados restantes (todos serão substituídos no batch)
- [ ] Atualizar README.md com o formato FUZ correto

## RUN 43 — 2026-10-23: 🏆 MISSÃO CUMPRIDA — 67.839 VOZES PT-BR INSTALADAS

### Batch completo
- 67.839/67.839 arquivos convertidos (xWMA → PCM 22050Hz mono 16-bit)
- **ZERO erros, ZERO parse_fail** — 11 workers × ffmpeg, ~15 minutos no M6
- Instalação: 67.839 bugados apagados, 67.839 novos movidos (mv, mesmo volume)
- Total: 12GB de vozes PCM em Data/sound/voice/ (loose files > BSA)

### Verificação (amostra aleatória)
- Elenwen (MQ101), Tullius (MQ302), DLC Dragonborn, NPCs genéricos: **todos PCM ✓ mono ✓ 22050Hz ✓**

### Confirmação do usuário (RUN 42, teste da intro)
> "deu certo. To muito feliz, o audio da intro do jogo é em portugues dublado
> e está muito de boa qualidade." — CleversonBamberg, 2026-10-23

### Estado final do áudio do projeto
| Sistema | Estado |
|---------|--------|
| Sons ambiente/ações/UI | ✅ nativo (XAudio2 PCM) |
| Música | ✅ 263 .xwm → .wav PCM soltos |
| Vozes | ✅ 67.839 .fuz xWMA → PCM (dublagem PT-BR completa) |
| LIP sync | ✅ preservado (data LIP original intacta nos .fuz) |

### Próximos passos possíveis
- [ ] Compressão APFS transparente nos .fuz (afsctool — 12GB → ~6GB, zero impacto no jogo)
- [ ] Extrair vozes vanilla do BSA (75.408 - as ~7.5k que o mod PT-BR não cobre) e converter também
- [ ] Converter músicas restantes

## RUN 44 — 2026-10-23: 🔑 PARSER BSA v105 DECIFRADO (de vez)

Layout completo do BSA Skyrim SE (version 105), validado matematicamente:
```
@0:       header 36B (magic, version=105, offset=36, aflags, fc, filec, tfnl, tfnl2, fflags)
@36:      folder records (fc × 24B: hash u64, count u32, unk u32, offset u64)
@36+fc×24: POR PASTA EM ORDEM: [u8 len_total INCLUINDO \0][nome+\0][count × file record 16B]
          file record: hash u64, size u32 (bits 30/31 = flags compressão), offset u32 (DIRETO, sem correção!)
depois:   bloco de file names (filec nomes null-terminated, = tfnl2 bytes)
fim:      DATA contíguo (na ordem dos records)
```
Aritmética de validação: 36 + fc×24 + Σ(1+len) + 16×filec + tfnl2 == data_start (bateu EXATO nos 2 BSAs).

### Resultados
- Voices_en0.bsa: 75.408 .fuz mapeados com nomes completos (record[0].size == FUZ[0] real ✓)
- Sounds.bsa: 6.198 arquivos (269 .xwm + 5.929 .wav) — extraídos os .xwm

## RUN 45 — Vozes inglesas nos diálogos sem dublagem PT-BR

- Diff BSA (75.408) vs PT-BR instalado (67.839) → **7.638 falas sem dublagem**
- Extraídas e convertidas (xWMA→PCM 22050Hz mono, 0 erros) e instaladas
- **Jogo agora com 75.477 falas audíveis** (67.839 PT-BR + 7.638 inglês nas não-dubladas)

## RUN 46 — Legendas PT-BR + música completa

### Tradução (Nexus 58406 "Skyrim - Tradução Completa" v6.0)
- Instalado conforme guia do autor: `Data/Strings/` (246 arquivos: base+DLC+Update+CC
  com nomes `_english` e conteúdo PT-BR) + `Data/interface/translate_*.txt`
- Amostra confirmada: "Túneis da Toca dos Ratos", "Por que você está procurando por um
  Draconato?" ✓
- sLanguage default (english) carrega os `_english.STRINGS` = PT-BR na prática — sem mexer em INI

### Música
- Os 269 .xwm do Sounds.bsa extraídos; 6 faltantes convertidos e instalados
  (5 do Creation Club + mus_combat_boss do CC bgssse016)
- **269/269 músicas agora tocam via .wav PCM loose**

### Estado final do projeto
| Sistema | Status |
|---------|--------|
| Gráficos/controles/gameplay | ✅ |
| Sons ambiente/ações/UI | ✅ nativo |
| Música | ✅ 269/269 (PCM loose) |
| Vozes PT-BR | ✅ 67.839 dubladas |
| Vozes inglês (não-dubladas) | ✅ 7.638 |
| Legendas PT-BR | ✅ mod 58406 instalado |
| LIP sync | ✅ preservado |

## RUN 47 — 2026-10-24: 🧰 FERRAMENTAS PRONTAS PRA COMUNIDADE (instalador 1-comando)

### Áudio stereo (resposta ao feedback do autor)
- 12.503 falas re-convertidas de mono→stereo 22050Hz (voicetypes malenord/femalenord
  — NPCs de Riverwood/Whiterun) para reduzir o pan 3D agressivo que o engine
  aplica a sons mono. Pendente: autor confirmar se estende pro resto.
- Compressão APFS aplicada ao jogo INTEIRO: 75.745 arquivos (vozes + músicas)
  via afsctool — PCM stereo com canal duplicado chega a 99% de economia
  (377KB → 4KB físicos). Livres: 6.3GB → 10GB.

### Ferramentas consolidadas no repo (o "produto" do projeto)
- `tools/bsa_extract.py` — extrator BSA v105 puro (parser do projeto, com
  --ext/--filter/--list/--skip-existing; validado nos 2 BSAs do jogo)
- `tools/patch_skyrimse_exe.py` — os 4 patches JE→JMP com verificação de
  versão e backup (idempotente)
- `tools/patch_steam_api.py` — agora idempotente (detecta 31 C0 C3 antes
  de re-patchear/backupar)
- `instalar-mac.sh` — **INSTALADOR COMPLETO EM 1 COMANDO**: detecta o jogo,
  instala ffmpeg via pip, aplica patches, converte dublagem PT-BR (se
  fornecida via PTBR=), extrai+converte as falas faltantes do BSA (inglês),
  converte as 269 músicas, instala strings de tradução (TRAD=), cria
  steam_appid.txt e comprime com afsctool. Idempotente — testado de ponta
  a ponta num jogo já instalado: pulou tudo, zero retrabalho.

### Divulgação (Nexus Mods)
- Não é possível distribuir os ARQUIVOS convertidos (~17GB, conteúdo
  Bethesda + dublagem/tradução de terceiros + limites de tamanho do Nexus).
- O caminho: publicar o REPOSITÓRIO como Utility (a comunidade baixa o
  próprio jogo/dublagem/tradução como "Requirements" e roda o instalador).

## RUN 48 — 2026-10-24: 🪄 ASSISTENTE DE 1-CLIQUE (INSTALAR.command)

Fluxo do usuário final (a visão do autor do projeto):
1. baixa o pacote → extrai
2. baixa dublagem/tradução (Nexus) e coloca os .7z na mesma pasta
3. duplo-clique em INSTALAR.command → assistente:
   [1] checa ambiente (arm64, python3)
   [2] localiza engine (engine/ local ou 3Pi2 → symlink automático)
   [3] cria prefixo (wineboot)
   [4] instala Steam (baixa SteamSetup da Valve se faltar)
   [5] espera login+download do Skyrim via Biblioteca
   [6] auto-detecta dublagem/tradução (.7z: olha o conteúdo, não o nome)
   [7] roda instalar-mac.sh (tudo já validado)
   [8] cria "Skyrim.command" na MESA — duplo-clique = sobe Steam + jogo
- tools/criar_atalho.sh: gerador do launcher (verifica Steam via tasklist,
  sobe em nohup, espera, lança)
- Testado: syntax ok, atalho gerado na Mesa do autor e funcional
- Licenças respeitadas: engine (Apple GPTK) e jogo (Steam) NÃO vão no
  pacote — o assistente baixa/orquestra das fontes oficiais
- docs/nexus-page.md: descrição EN+PT pronta pra página do Nexus

## RUN 49 — 2026-10-26: 🇺🇸 VOZES ORIGINAIS INGLESAS EM QUALIDADE NATIVA (decisão do autor)

### Contexto
Após testar a campanha, o autor avaliou: a conversão estava boa, mas a DUBLAGEM
do mod PT-BR (#105861) é gerada por IA — sotaque inconsistente entre personagens,
não soa natural. Decisão: vozes ORIGINAIS em inglês + legendas PT-BR (a tradução
#58406 é dos textos originais — sincroniza perfeitamente com o áudio EN).

### Teste A/B (metodologia)
Mesma fala (Hadvar, MQ101) convertida em 44.1kHz stereo nas duas versões e
tocada direto no macOS (afplay): autor confirmou qualidade da conversão OK —
o problema era a dublagem em si.

### Execução — tools/voz_nativa_lotes.py
- 75.408 falas extraídas do BSA vanilla e convertidas SEM downsample
  (44.1kHz nativo, canal nativo — as originais são mono 44.1kHz, fiel ao jogo)
- Lotes de ~2.500 por voicetype, compressão APFS (afsctool) entre lotes
- Guard de espaço (parou seguro no lote 23 com 1.7GB livres)
- Liberação: music-backup (3.3GB, redundante) + dublagem IA (2.6GB,
  re-baixável no Nexus #105861) → incremental completou os 4.574 restantes
- Incidente do mv pro disco interno: falhou (disco interno 100% cheio) —
  BSA permaneceu íntegro no Data (verificado byte a byte: 1.805.869.173)
- MODO INCREMENTAL adicionado (VOZ_INCREMENTAL=1: pula instaladas, não apaga)

### Estado final
- 75.408/75.408 vozes inglesas (44.1kHz nativo) | 0 erros reais
- Legendas PT-BR mantidas (246 strings) — modo "legendado"
- LIP sync preservado | 6.3GB livres | atalho na Mesa funcional
- Rollback da dublagem: re-baixar Nexus #105861 + PTBR= ./instalar-mac.sh
