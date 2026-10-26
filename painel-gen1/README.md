# Painel da Living Dex Gen 1 (mGBA + OBS)

Painel pro seu computador que acompanha uma Living Dex de **Pokémon Red, Blue e Yellow** jogada no **mGBA**. Feito pela Poké Prof. Bella (OTBella) para a Missão Living Dex.

Ele junta três coisas:

- **O guia da Gen 1** ([versão online](https://pokeprofbella.github.io/livingdex/gen1/)) rodando no seu computador, com um painel lateral.
- **Um script pro mGBA** que lê a memória do jogo aberto (só lê, nunca mexe no save).
- **Arquivos pro OBS**, que se atualizam sozinhos durante a live.

## O que ele faz

- **Marca sozinho** no guia cada captura, presente, troca e evolução. Aparece um aviso com o botão **Desfazer**, caso tenha sido engano.
- **Conta os encontros** selvagens, mas só quando você está no lugar onde aparece o próximo alvo. Zera a cada captura.
- **Próximo alvo** com sprite, nome e onde pegar, seguindo a Ordem do jogo do save que está aberto.
- **Time** com sprite, apelido e nível de cada Pokémon.
- **Box atual** (ex.: `Box 3 · 14/20` ou `Box 3 · CHEIA`), pra você não encher a box sem perceber.
- **Máquina sortuda do Game Corner**: quando você entra no Game Corner, o painel mostra qual máquina sorteou.
- **Suas boxes de verdade** no guia (aba Boxes → botão "Ver minhas boxes do jogo"), com apelido e nível, lidas do arquivo .sav.
- Troca de save sozinha: abriu o Red no mGBA, o guia passa pro save de Red.

Tudo roda só no seu computador. Nada é enviado pra internet.

## Do que você precisa

- **mGBA 0.10 ou mais novo** ([mgba.io](https://mgba.io)).
- Sua cópia de **Pokémon Red, Blue ou Yellow em inglês (versão americana)**. O script lê endereços de memória dessas versões; outras línguas não funcionam.
- **Python 3**:
  - **Mac:** abra o Terminal e digite `python3 --version`. Se pedir pra instalar as ferramentas de desenvolvedor, aceite. Ou baixe em [python.org](https://www.python.org/downloads/).
  - **Windows:** baixe em [python.org](https://www.python.org/downloads/). Na primeira tela do instalador, marque **"Add python.exe to PATH"**.
- OBS (opcional, só se for fazer live).

## Instalação

1. Baixe o [painel-gen1.zip](https://github.com/pokeprofbella/livingdex/raw/main/painel-gen1.zip) e descompacte onde quiser (ex.: Documentos). Os arquivos pro OBS são gravados nesta pasta, então não mude ela de lugar depois de configurar o OBS.
2. **Abra o painel:**
   - **Mac:** dois cliques em `Abrir Painel.command`. Na primeira vez o Mac pode bloquear: clique com o botão direito → **Abrir** → **Abrir**.
   - **Windows:** dois cliques em `Abrir Painel.bat`.
   - Abre uma janela preta (deixe aberta durante o jogo) e o guia no navegador, em `http://127.0.0.1:8765/gen1`.
3. **Carregue o script no mGBA:** abra o jogo, vá em **Tools → Scripting…**, depois **File → Load script** e escolha `missao_gen1.lua`. Na janela do script aparece `Missão Gen 1 carregado. Deixe o painel aberto.`
4. (Opcional) **Boxes de verdade:** abra `server.py` num editor de texto e preencha `PASTA_DOS_SAVES` com a pasta onde ficam os seus `.sav` (normalmente a mesma pasta da ROM). Feche e abra o painel de novo.

O mGBA lembra os últimos scripts em **File → Load recent script**.

## Usando no dia a dia

- No guia, o **painel lateral** mostra o save, o próximo alvo, os encontros e o que falta na parte atual.
- **Encontros:** contam sozinhos. Pra corrigir na mão, use os botões +1 / −1, ou as teclas `+` e `−` com o guia em foco.
- **Capturas:** o script avisa o guia, que marca sozinho. Também dá pra marcar clicando no círculo do card, como no site.
- **Save:** "Automático" segue o jogo aberto no mGBA. Dá pra escolher na mão.
- O progresso fica em `progresso_gen1.json`, nesta pasta. Faça uma cópia de vez em quando.
- **Levar pro site:** o botão no topo gera um código `LDX1-…` que você cola no [guia online](https://pokeprofbella.github.io/livingdex/gen1/) pra ver seu progresso no celular.

## Arquivos pro OBS

Todos ficam nesta pasta. Nas fontes de texto do OBS, marque **"Ler de arquivo"** e escolha o arquivo.

| Arquivo | Tipo de fonte no OBS | O que mostra |
|---|---|---|
| `dex_atual.txt` | Texto | `42 / 151` |
| `capturas.txt` | Texto | Quantas capturas você marcou (ex.: `57`) |
| `encontros.txt` | Texto | Encontros desde a última captura |
| `proximo_alvo.txt` | Texto | Nome do próximo alvo |
| `proximo_alvo.png` | Imagem | Sprite do próximo alvo (56×56: use escala 2× ou 3× e filtro "Ponto") |
| `proximo_alvo_local.txt` | Texto | Onde pegar o próximo alvo |
| `selo_aqui_atual.png` | Imagem | Selo "Aqui" quando você está no lugar do alvo (some quando não está) |
| `objetivos.txt` | Texto | Objetivos da parte atual |
| `time_1.png` … `time_6.png` | Imagem | Sprites do time |
| `time_1_nome.txt` … `time_6_nome.txt` | Texto | Apelido (ou nome da espécie) |
| `time_1_nivel.txt` … `time_6_nivel.txt` | Texto | `Nv. 23` |
| `box_atual.txt` | Texto | `Box 3 · 14/20` |
| `maquina_sortuda.txt` | Texto | Máquina sortuda do Game Corner |
| `local_atual.txt` | Texto | Onde você está agora |

**Lista de objetivos bonitinha:** adicione uma fonte **Navegador** com o endereço `http://127.0.0.1:8765/overlay/objetivos`, largura 360 e altura 281. Ela mostra o lugar atual, o que tem pra pegar ali e a máquina sortuda quando você está no Game Corner. Fundo transparente.

**Meta do contador de capturas:** se quiser `57 / 151` em vez de só `57`, mude `CAPTURAS_TOTAL` em `server.py`.

## Problemas comuns

- **"Não achei o painel em 127.0.0.1:8765"** no mGBA: o painel não está aberto. Abra o `Abrir Painel` e recarregue o script.
- **O guia diz "Painel offline":** a janela preta foi fechada. Abra o `Abrir Painel` de novo.
- **Nada acontece no jogo:** confira se o jogo é Red, Blue ou Yellow em inglês (EUA) e se o script está carregado (Tools → Scripting).
- **Os encontros não sobem:** eles só contam no lugar onde aparece o próximo alvo. Isso é proposital.
- **Carreguei um save antigo ou um savestate:** o script percebe pela hora de jogo e pelo ID do treinador e não marca nada errado.
- **Outra coisa usando a porta 8765:** troque `PORT` em `server.py` e `PORT` no começo de `missao_gen1.lua` pro mesmo número.

## Créditos

Endereços de memória, charset e máquinas do Game Corner: projeto [pret](https://github.com/pret) (pokered e pokeyellow). Dados do guia: Serebii, Bulbapedia, The Cave of Dragonflies, PokeAPI e o guia de Living Dex da [Lyra](https://lyra-made-a.website/pokemon_gen1/full_guide).

Projeto de fã, sem afiliação com Nintendo, Game Freak, Creatures ou The Pokémon Company. Pokémon e todos os nomes e imagens relacionados são marcas e propriedade de seus donos. O código pode ser usado e adaptado à vontade (licença MIT, veja `LICENSE`). Se usar na sua live, um crédito à OTBella é muito bem-vindo.
