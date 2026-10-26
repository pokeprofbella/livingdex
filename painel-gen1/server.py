from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse
import json, webbrowser, threading, sys, base64, time, shutil, unicodedata, re

# ================= CONFIGURAÇÃO =================
# Pasta onde o mGBA grava os .sav (normalmente a mesma pasta da ROM).
# Com ela, o guia mostra as 12 boxes de verdade do seu save. Sem ela, mostra só o time e a box aberta.
#   Mac:     PASTA_DOS_SAVES = '~/Jogos/GameBoy'
#   Windows: PASTA_DOS_SAVES = r'C:\Jogos\GameBoy'
PASTA_DOS_SAVES = ''
# Meta do contador de capturas (capturas.txt). 0 = mostra só o número.
CAPTURAS_TOTAL = 0
# =================================================

BASE = Path(__file__).resolve().parent
HOST = '127.0.0.1'; PORT = 8765
F = {'dex': BASE/'dex_atual.txt', 'bank': BASE/'capturas.txt', 'target': BASE/'proximo_alvo.txt',
     'enc': BASE/'encontros.txt', 'obj': BASE/'objetivos.txt',
     'loc': BASE/'proximo_alvo_local.txt', 'places': BASE/'alvos_por_local.json',
     'tasks': BASE/'tarefas.json', 'here': BASE/'local_atual.txt'}
OVL = BASE/'overlay_objetivos.html'
PROG = BASE/'progresso_gen1.json'   # checkboxes do guia da Gen 1
GUIA = BASE/'guia_gen1.html'

def frac(t, a, b):
    try:
        x, y = t.strip().split('/', 1); return int(x.strip()), int(y.strip())
    except Exception: return a, b
def intval(t, d=0):
    try: return int(t.strip().split()[0])
    except Exception: return d

DEX_TOTAL = 151
def fixa(s):
    s['bank_total'] = CAPTURAS_TOTAL; s['dex_total'] = DEX_TOTAL
    return s

def load():
    s = {'dex_current': 0, 'dex_total': DEX_TOTAL, 'bank_current': 0, 'bank_total': CAPTURAS_TOTAL, 'target': '—', 'encounters': 0}
    if F['dex'].exists(): s['dex_current'], s['dex_total'] = frac(F['dex'].read_text(encoding='utf-8'), 0, DEX_TOTAL)
    if F['bank'].exists(): s['bank_current'], s['bank_total'] = (intval(F['bank'].read_text(encoding='utf-8'), 0), CAPTURAS_TOTAL)
    if F['target'].exists(): s['target'] = F['target'].read_text(encoding='utf-8').strip() or '—'
    if F['enc'].exists(): s['encounters'] = intval(F['enc'].read_text(encoding='utf-8'), 0)
    return fixa(s)

def save(s):
    fixa(s)
    F['dex'].write_text(f"{int(s['dex_current'])} / {int(s['dex_total'])}\n", encoding='utf-8')
    F['bank'].write_text((f"{int(s['bank_current'])} / {int(s['bank_total'])}" if int(s['bank_total']) else f"{int(s['bank_current'])}") + "\n", encoding='utf-8')
    F['target'].write_text(f"{str(s.get('target', '—')).strip() or '—'}\n", encoding='utf-8')
    F['enc'].write_text(f"{int(s['encounters'])}\n", encoding='utf-8')

def write_atomic(p, text):
    tmp = p.with_suffix(p.suffix + '.tmp'); tmp.write_text(text, encoding='utf-8'); tmp.replace(p)


# ---------------- Script do mGBA (Gen 1) ----------------
EMU = BASE/'emu_estado.json'          # último estado recebido do mGBA
SPR = BASE/'sprites_gen1'             # 001.png … 151.png (Yellow, 56×56)
VAZIO = BASE/'vazio.png'
SELO = BASE/'selo_aqui.png'
def _json(p, d):
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception: return d
NOMES = {int(k): v for k, v in _json(BASE/'nomes_gen1.json', {}).items()}
MAPAS = _json(BASE/'mapas_gen1.json', [])
LUGARES = _json(BASE/'lugares_gen1.json', [])
AREAS = {'Center': 'Centro', 'East': 'Leste', 'North': 'Norte', 'West': 'Oeste'}
# Máquinas do Game Corner na ordem interna do jogo (pret/pokered, hidden_events GAME_CORNER)
SLOTS = [(18,15),(18,14),(18,13),(18,12),(18,11),(18,10),(13,10),(13,11),(13,12),(13,13),(13,14),(13,15),
         (12,15),(12,14),(12,13),(12,12),(12,11),(12,10),(7,10),(7,11),(7,12),(7,13),(7,14),(7,15),
         (6,15),(6,14),(6,13),(6,12),(6,11),(6,10),(1,10),(1,11),(1,12),(1,13),(1,14),(1,15)]
QUEBRADAS = {5, 8, 27}
COLUNA = {1: 1, 6: 2, 7: 3, 12: 4, 13: 5, 18: 6}

def _norm(t):
    t = unicodedata.normalize('NFD', t)
    return re.sub(r"[\u0300-\u036f'’.]", '', t).lower()

def lugar(map_id):
    """Nome do mapa no padrão do guia: 'Mt. Moon · B2F', 'Safari Zone · Centro'."""
    if not (0 <= map_id < len(MAPAS)): return ''
    nome = MAPAS[map_id]
    base, _, andar = nome.partition(' · ')
    nb = _norm(base)
    melhor = ''
    for L in LUGARES:
        nl = _norm(L)
        if (nb == nl or nb.startswith(nl + ' ')) and len(L) > len(melhor): melhor = L
    if not melhor: return nome
    resto = base[len(melhor):].strip() if _norm(base[:len(melhor)]) == _norm(melhor) else ''
    resto = AREAS.get(resto, resto)
    partes = [melhor] + [x for x in (resto, andar) if x]
    return ' · '.join(partes)

def sortuda_txt(v):
    if v is None or v < 0: return ''
    if v == 0: return 'Sem máquina sortuda agora: saia e entre de novo'
    i = v - 1
    if i in QUEBRADAS or i >= len(SLOTS): return 'Sem máquina sortuda agora: saia e entre de novo'
    x, y = SLOTS[i]
    return f'Máquina sortuda: coluna {COLUNA[x]} (da esquerda), {y - 9}ª de cima'

def _copy(src, dst):
    tmp = dst.with_suffix(dst.suffix + '.tmp'); shutil.copyfile(src, tmp); tmp.replace(dst)

def no_lugar_do_alvo(here=None):
    """True quando você está no lugar onde o próximo alvo aparece (compara só o nome do lugar, sem andar/área)."""
    if here is None: here = F['here'].read_text(encoding='utf-8').strip() if F['here'].exists() else ''
    alvo = F['loc'].read_text(encoding='utf-8').strip() if F['loc'].exists() else ''
    return bool(here) and bool(alvo) and _norm(here.split(' · ')[0]) == _norm(alvo.split(' · ')[0])

def atualiza_selo():
    on = no_lugar_do_alvo()
    if SELO.exists() and VAZIO.exists(): _copy(SELO if on else VAZIO, BASE/'selo_aqui_atual.png')

def emu_vivo():
    d = _json(EMU, {})
    return d if d and time.time() - d.get('_t', 0) < 30 else None

# Charset da Gen 1 (pret/pokeyellow constants/charmap.asm) pros apelidos
_CH = {0x7F: ' ', 0x9A: '(', 0x9B: ')', 0x9C: ':', 0x9D: ';', 0x9E: '[', 0x9F: ']', 0xBA: 'é', 0xBB: "'d", 0xBC: "'l",
       0xBD: "'s", 0xBE: "'t", 0xBF: "'v", 0xE0: "'", 0xE1: 'PK', 0xE2: 'MN', 0xE3: '-', 0xE4: "'r", 0xE5: "'m", 0xE6: '?',
       0xE7: '!', 0xE8: '.', 0xEF: '♂', 0xF0: '¥', 0xF1: '×', 0xF2: '.', 0xF3: '/', 0xF4: ',', 0xF5: '♀'}
_CH.update({0x80 + i: chr(65 + i) for i in range(26)}); _CH.update({0xA0 + i: chr(97 + i) for i in range(26)})
_CH.update({0xF6 + i: str(i) for i in range(10)})

def apelido(m):
    """Apelido do Pokémon do time; se for o nome padrão da espécie (MAIÚSCULO), usa o nome bonito da espécie."""
    nome = NOMES.get(int(m['dex']), '') if m and m.get('dex') else ''
    try:
        bs = bytes.fromhex(m.get('nk') or '')
    except Exception:
        return nome
    t = ''
    for c in bs:
        if c == 0x50: break
        t += _CH.get(c, '')
    t = t.strip()
    k = lambda x: re.sub(r"[\s'’.]", '', _norm(x))
    if not t or k(t) == k(nome): return nome
    return t

# ---------- Boxes do jogo (pra saber o apelido e onde cada um está) ----------
TO_DEX = {1:112,2:115,3:32,4:35,5:21,6:100,7:34,8:80,9:2,10:103,11:108,12:102,13:88,14:94,15:29,16:31,17:104,18:111,19:131,20:59,21:151,22:130,23:90,24:72,25:92,26:123,27:120,28:9,29:127,30:114,33:58,34:95,35:22,36:16,37:79,38:64,39:75,40:113,41:67,42:122,43:106,44:107,45:24,46:47,47:54,48:96,49:76,51:126,53:125,54:82,55:109,57:56,58:86,59:50,60:128,64:83,65:48,66:149,70:84,71:60,72:124,73:146,74:144,75:145,76:132,77:52,78:98,82:37,83:38,84:25,85:26,88:147,89:148,90:140,91:141,92:116,93:117,96:27,97:28,98:138,99:139,100:39,101:40,102:133,103:136,104:135,105:134,106:66,107:41,108:23,109:46,110:61,111:62,112:13,113:14,114:15,116:85,117:57,118:51,119:49,120:87,123:10,124:11,125:12,126:68,128:55,129:97,130:42,131:150,132:143,133:129,136:89,138:99,139:91,141:101,142:36,143:110,144:53,145:105,147:93,148:63,149:65,150:17,151:18,152:121,153:1,154:3,155:73,157:118,158:119,163:77,164:78,165:19,166:20,167:33,168:30,169:74,170:137,171:142,173:81,176:4,177:7,178:5,179:8,180:6,185:43,186:44,187:45,188:69,189:70,190:71}   # espécie interna → nº da dex
ROMS = Path(PASTA_DOS_SAVES).expanduser() if PASTA_DOS_SAVES.strip() else None   # onde o mGBA grava o .sav
BOX_SIZE = 0x462

def _apelido_bytes(dex, bs):
    return apelido({'dex': dex, 'nk': bs.split(b'\x50')[0].hex() + '50'})

def _box_do_sav(f, off):
    n = f[off]
    if n > 20: return None                   # box nunca usada (lixo no .sav)
    mons = []
    for i in range(n):
        dx = TO_DEX.get(f[off + 1 + i], 0)
        nk = f[off + 1 + 21 + 660 + 220 + i * 11: off + 1 + 21 + 660 + 220 + i * 11 + 11]
        mons.append({'dex': dx, 'nome': NOMES.get(dx, '?'), 'apelido': _apelido_bytes(dx, nk), 'lv': f[off + 1 + 21 + i * 33 + 3]})
    return mons

def sav_do_jogo(jogo):
    chave = {'Yellow': 'yellow', 'Red': 'red', 'Blue': 'blue'}.get(jogo or '')
    if not chave or ROMS is None or not ROMS.exists(): return None
    L = [x for x in ROMS.glob('*.sav') if re.search(r'(^|[^a-z])' + chave + r'([^a-z]|$)', x.name.lower())]
    return max(L, key=lambda x: x.stat().st_mtime) if L else None

def boxes_estado():
    """Time e as 12 boxes: o .sav dá as boxes como estavam no último save; a box aberta e o time vêm ao vivo do mGBA."""
    e = emu_vivo() or _json(EMU, {})
    jogo = e.get('jogo')
    out = {'jogo': jogo, 'vivo': bool(emu_vivo()), 'sav': None, 'sav_t': None, 'atual': None, 'caixas': [], 'time': []}
    out['time'] = [{'dex': int(m['dex']), 'nome': NOMES.get(int(m['dex']), '?'), 'apelido': apelido(m), 'lv': m.get('lv')} for m in (e.get('time') or []) if m and m.get('dex')]
    caixas = {}
    sv = sav_do_jogo(jogo)
    if sv:
        f = sv.read_bytes()
        if len(f) >= 0x8000:
            if not out['time'] or not emu_vivo():          # sem mGBA aberto: time do último save
                pc = min(f[0x2F2C], 6); out['time'] = []
                for i in range(pc):
                    dx = TO_DEX.get(f[0x2F2C + 1 + i], 0)
                    nk = f[0x2F2C + 8 + 6 * 44 + 6 * 11 + i * 11: 0x2F2C + 8 + 6 * 44 + 6 * 11 + i * 11 + 11]
                    out['time'].append({'dex': dx, 'nome': NOMES.get(dx, '?'), 'apelido': _apelido_bytes(dx, nk), 'lv': f[0x2F2C + 8 + i * 44 + 0x21]})
            out['sav'] = sv.name; out['sav_t'] = sv.stat().st_mtime
            cb = f[0x284C]
            atual = (cb & 0x7F) + 1
            for i in range(12):
                off = (0x4000 if i < 6 else 0x6000) + (i % 6) * BOX_SIZE
                caixas[i + 1] = _box_do_sav(f, off) if (cb & 0x80) else None
            caixas[atual] = _box_do_sav(f, 0x30C0)     # a box aberta fica salva noutro lugar
            out['atual'] = atual
    cx = e.get('caixa')
    if cx and emu_vivo():                            # ao vivo ganha do .sav
        mons = []
        nks = cx.get('nk') or []
        for i_, d_ in enumerate(cx.get('sp') or []):
            h = nks[i_] if i_ < len(nks) else ''
            lvs = cx.get('lv') or []
            mons.append({'dex': int(d_), 'nome': NOMES.get(int(d_), '?'), 'apelido': apelido({'dex': d_, 'nk': h}), 'lv': lvs[i_] if i_ < len(lvs) else None})
        caixas[int(cx['num'])] = mons; out['atual'] = int(cx['num'])
    out['caixas'] = [{'num': i, 'n': len(caixas.get(i) or []), 'mons': caixas.get(i) or []} for i in range(1, 13)]
    return out

def recebe_emu(b):
    d = _json(EMU, {})
    d.update({k: b.get(k) for k in ('jogo', 'mapa', 'batalha', 'inimigo', 'box', 'pokedex', 'caixa')})
    d['_t'] = time.time()
    d['local'] = lugar(int(b.get('mapa', -1)))
    d['sortuda'] = sortuda_txt(b.get('sortuda', -1))
    write_atomic(F['here'], d['local'] + '\n')
    write_atomic(BASE/'maquina_sortuda.txt', d['sortuda'] + '\n')
    cx = b.get('caixa')                                          # box aberta no PC, pro OBS
    if cx: write_atomic(BASE/'box_atual.txt', (f"Box {cx['num']} · CHEIA" if len(cx.get('sp') or []) >= 20 else f"Box {cx['num']} · {len(cx.get('sp') or [])}/20") + '\n')
    # time no OBS: time_N.png / time_N_nome.txt / time_N_nivel.txt
    time_ = b.get('time') or []
    for n in range(1, 7):
        m = time_[n - 1] if n <= len(time_) else None
        png = SPR/f"{int(m['dex']):03d}.png" if m and m.get('dex') else None
        if png is not None and png.exists(): _copy(png, BASE/f'time_{n}.png')
        elif VAZIO.exists(): _copy(VAZIO, BASE/f'time_{n}.png')
        write_atomic(BASE/f'time_{n}_nome.txt', (apelido(m) if m else '') + '\n')     # apelido; sem apelido = nome da espécie
        write_atomic(BASE/f'time_{n}_nivel.txt', (f"Nv. {m['lv']}" if m else '') + '\n')
    d['time'] = time_
    # eventos: encontro soma sozinho (só no lugar do próximo alvo); captura e evolução viram sugestão que o guia marca sozinho
    for ev in b.get('eventos') or []:
        t = ev.get('tipo')
        if t == 'encontro' and no_lugar_do_alvo(d['local']):   # só conta no lugar onde o próximo alvo aparece
            s = load(); s['encounters'] += 1; save(s)
        elif t in ('novo', 'evolucao') and ev.get('dex'):
            d.setdefault('sugestoes', []).append({'tipo': t, 'dex': int(ev['dex']), 'nome': NOMES.get(int(ev['dex']), '?'),
                             'origem': ev.get('origem', ''), 'de': NOMES.get(int(ev.get('de') or 0), ''), 'de_dex': int(ev.get('de') or 0), 'id': time.time()})
            d['sugestoes'] = d['sugestoes'][-10:]
    write_atomic(EMU, json.dumps(d, ensure_ascii=False))
    atualiza_selo()

def tasks_state():
    d = json.loads(F['tasks'].read_text(encoding='utf-8')) if F['tasks'].exists() else {}
    here = F['here'].read_text(encoding='utf-8').strip() if (F['here'].exists() and emu_vivo()) else ''   # escrito pelo script do mGBA
    d['local'] = None
    if here:
        places = json.loads(F['places'].read_text(encoding='utf-8')) if F['places'].exists() else {}
        base = here.split(' · ')[0]
        aqui = next((v for k, v in places.items() if k.split(' (')[0] == base), [])
        d['local'] = {'nome': here, 'base': base, 'aqui': aqui}
        st = (emu_vivo() or {}).get('sortuda') or ''
        if st and base == 'Game Corner':                     # dentro do Game Corner o topo mostra a máquina sortuda
            d['local']['sortuda'] = st.replace('Máquina sortuda: ', 'Máquina sortuda: ').replace(' (da esquerda)', '')
    return d

class H(BaseHTTPRequestHandler):
    def out(self, c, b, ct='text/html; charset=utf-8'):
        try:
            self.send_response(c); self.send_header('Content-Type', ct); self.send_header('Cache-Control', 'no-store')
            self.end_headers(); self.wfile.write(b)
        except (BrokenPipeError, ConnectionResetError):
            pass  # o script do mGBA envia e fecha sem esperar a resposta; o dado já foi gravado
    def js(self, obj, c=200): self.out(c, json.dumps(obj, ensure_ascii=False).encode(), 'application/json; charset=utf-8')
    def body(self):
        n = int(self.headers.get('Content-Length', '0')); return json.loads(self.rfile.read(n).decode() or '{}')

    def do_GET(self):
        p = urlparse(self.path).path
        if p in ('/', '/gen1', '/gen1/'): self.out(200, GUIA.read_bytes())
        elif p == '/state':
            st = load(); e = emu_vivo()
            st['emu'] = {'local': e.get('local'), 'sortuda': e.get('sortuda'), 'sugestoes': e.get('sugestoes', []), 'jogo': e.get('jogo'),
                         'box': ({'num': e['caixa'].get('num'), 'n': len(e['caixa'].get('sp') or [])} if e.get('caixa') else None)} if e else None
            self.js(st)
        elif p in ('/overlay/objetivos', '/overlay/objetivos/'): self.out(200, OVL.read_bytes())
        elif p == '/g1/tarefas': self.js(tasks_state())
        elif p == '/g1/boxes': self.js(boxes_estado())
        elif p == '/g1/progress': self.js(json.loads(PROG.read_text(encoding='utf-8')) if PROG.exists() else {})
        else: self.out(404, b'Not found', 'text/plain')

    def do_POST(self):
        p = urlparse(self.path).path
        try:
            b = self.body()
            if p == '/g1/progress':                # checkboxes da Gen 1
                write_atomic(PROG, json.dumps(b, ensure_ascii=False, indent=1)); return self.js({'ok': True})
            if p == '/g1/obs':                     # alvo, objetivos e dex calculados pelo guia
                s = load(); s['target'] = b.get('target', '—')
                s['dex_current'], s['dex_total'] = frac(b.get('dex', ''), s['dex_current'], s['dex_total'])
                save(s); write_atomic(F['obj'], b.get('objetivos', '').strip() + '\n')
                write_atomic(F['loc'], (b.get('local') or '').strip() + '\n')      # onde pegar o próximo alvo
                write_atomic(F['places'], json.dumps(b.get('lugares') or {}, ensure_ascii=False))  # pro selo do script do mGBA
                if b.get('painel'): write_atomic(F['tasks'], json.dumps(b['painel'], ensure_ascii=False))  # lista do overlay
                if b.get('sprite'):                # sprite do próximo alvo pro OBS (PNG 56×56)
                    tmp = BASE/'proximo_alvo.png.tmp'; tmp.write_bytes(base64.b64decode(b['sprite'])); tmp.replace(BASE/'proximo_alvo.png')
                atualiza_selo()
                return self.js({'ok': True})
            if p == '/g1/emu':                     # script do mGBA
                recebe_emu(b); return self.js({'ok': True})
            if p == '/g1/ack':                     # guia respondeu à sugestão de captura/evolução
                d = _json(EMU, {})
                d['sugestoes'] = [x for x in d.get('sugestoes', []) if x.get('id') != b.get('id')]; write_atomic(EMU, json.dumps(d, ensure_ascii=False))
                return self.js({'ok': True})
            if p == '/g1/count':                   # encontros e PKMN Salvos
                s = load()
                if 'encounters' in b: s['encounters'] = max(0, int(b['encounters']))
                s['encounters'] = max(0, s['encounters'] + int(b.get('enc_delta', 0)))
                s['bank_current'] = max(0, s['bank_current'] + int(b.get('bank_delta', 0)))
                save(s); return self.js(s)
            self.out(404, b'Not found', 'text/plain')
        except Exception as e:
            self.js({'ok': False, 'error': str(e)}, 400)
    def log_message(self, *args): pass

if __name__ == '__main__':
    page = sys.argv[1] if len(sys.argv) > 1 else 'gen1'
    url = f'http://{HOST}:{PORT}/{page}'
    try:
        srv = HTTPServer((HOST, PORT), H)
    except OSError:                                # já está rodando: só abre a página
        webbrowser.open(url); sys.exit(0)
    save(load())
    if not F['obj'].exists(): F['obj'].write_text('\n', encoding='utf-8')
    threading.Timer(.8, lambda: webbrowser.open(url)).start()
    print(f'Painel da Gen 1 aberto em http://{HOST}:{PORT}/gen1  (deixe esta janela aberta durante a live; feche pra desligar)')
    srv.serve_forever()
