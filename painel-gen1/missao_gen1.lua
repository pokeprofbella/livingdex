-- Missão Living Dex · Gen 1 · script da live pro mGBA (0.10+)
-- Lê a memória do Red/Blue/Yellow (versão americana) e manda pro painel (server.py):
--   encontros selvagens, capturas, evoluções, time, local atual e máquina sortuda do Game Corner.
-- Só LÊ a memória. Não altera nada no save.
-- Como usar: abra o painel (Abrir Painel.command no Mac, Abrir Painel.bat no Windows) e, no mGBA,
-- Tools → Scripting… → File → Load script → este arquivo. Guia completo: README.md

local HOST, PORT = "127.0.0.1", 8765

local ADDR = {
  RB = {curMap=0xD35E, inBattle=0xD057, battleType=0xD05A, enemySp=0xCFE5, enemyLv=0xCFF3,
        partyCount=0xD163, partySp=0xD164, partyLv1=0xD18C, boxCount=0xDA80, owned=0xD2F7, lucky=0xCD05,
        playerID=0xD359, ptH=0xDA41, ptM=0xDA43, ptS=0xDA44, partyNick=0xD2B5, curBox=0xD5A0, boxSp=0xDA81, boxNick=0xDE06, boxMons=0xDA96},
  Y  = {curMap=0xD35D, inBattle=0xD056, battleType=0xD059, enemySp=0xCFE4, enemyLv=0xCFF2,
        partyCount=0xD162, partySp=0xD163, partyLv1=0xD18B, boxCount=0xDA7F, owned=0xD2F6, lucky=0xCD05,
        playerID=0xD358, ptH=0xDA40, ptM=0xDA42, ptS=0xDA43, partyNick=0xD2B4, curBox=0xD59F, boxSp=0xDA80, boxNick=0xDE05, boxMons=0xDA95},
}
local PARTY_MON_SIZE = 0x2C
local GAME_CORNER = 135
local TO_DEX = {[1]=112,[2]=115,[3]=32,[4]=35,[5]=21,[6]=100,[7]=34,[8]=80,[9]=2,[10]=103,[11]=108,[12]=102,[13]=88,[14]=94,[15]=29,[16]=31,[17]=104,[18]=111,[19]=131,[20]=59,[21]=151,[22]=130,[23]=90,[24]=72,[25]=92,[26]=123,[27]=120,[28]=9,[29]=127,[30]=114,[33]=58,[34]=95,[35]=22,[36]=16,[37]=79,[38]=64,[39]=75,[40]=113,[41]=67,[42]=122,[43]=106,[44]=107,[45]=24,[46]=47,[47]=54,[48]=96,[49]=76,[51]=126,[53]=125,[54]=82,[55]=109,[57]=56,[58]=86,[59]=50,[60]=128,[64]=83,[65]=48,[66]=149,[70]=84,[71]=60,[72]=124,[73]=146,[74]=144,[75]=145,[76]=132,[77]=52,[78]=98,[82]=37,[83]=38,[84]=25,[85]=26,[88]=147,[89]=148,[90]=140,[91]=141,[92]=116,[93]=117,[96]=27,[97]=28,[98]=138,[99]=139,[100]=39,[101]=40,[102]=133,[103]=136,[104]=135,[105]=134,[106]=66,[107]=41,[108]=23,[109]=46,[110]=61,[111]=62,[112]=13,[113]=14,[114]=15,[116]=85,[117]=57,[118]=51,[119]=49,[120]=87,[123]=10,[124]=11,[125]=12,[126]=68,[128]=55,[129]=97,[130]=42,[131]=150,[132]=143,[133]=129,[136]=89,[138]=99,[139]=91,[141]=101,[142]=36,[143]=110,[144]=53,[145]=105,[147]=93,[148]=63,[149]=65,[150]=17,[151]=18,[152]=121,[153]=1,[154]=3,[155]=73,[157]=118,[158]=119,[163]=77,[164]=78,[165]=19,[166]=20,[167]=33,[168]=30,[169]=74,[170]=137,[171]=142,[173]=81,[176]=4,[177]=7,[178]=5,[179]=8,[180]=6,[185]=43,[186]=44,[187]=45,[188]=69,[189]=70,[190]=71}

local A, GAME = nil, "?"
local buf = console:createBuffer("Missão Gen 1")
local status = "iniciando"

-- ---------- JSON mínimo ----------
local function enc(v)
  local t = type(v)
  if t == "number" then return tostring(math.floor(v)) end
  if t == "boolean" then return v and "true" or "false" end
  if t == "string" then return '"' .. v:gsub('[%c"\\]', function(c) return string.format("\\u%04x", c:byte()) end) .. '"' end
  if t == "table" then
    if #v > 0 or next(v) == nil then local o = {} for i = 1, #v do o[i] = enc(v[i]) end return "[" .. table.concat(o, ",") .. "]" end
    local o = {} for k, x in pairs(v) do o[#o + 1] = enc(tostring(k)) .. ":" .. enc(x) end return "{" .. table.concat(o, ",") .. "}"
  end
  return "null"
end

-- ---------- envio pro painel ----------
local failed = false
local function post(path, payload)
  local body = enc(payload)
  local ok, err = pcall(function()
    local s = socket.connect(HOST, PORT)
    if not s then error("sem conexão") end
    s:send("POST " .. path .. " HTTP/1.0\r\nHost: " .. HOST .. "\r\nContent-Type: application/json\r\nContent-Length: " .. #body .. "\r\n\r\n" .. body)
    pcall(function() s:receive(512) end)
    s:close()
  end)
  if ok then
    if failed then console:log("Painel conectado de novo.") end
    failed = false; status = "painel conectado"
  else
    if not failed then console:log("Não achei o painel em " .. HOST .. ":" .. PORT .. ". Abra o Abrir Painel (.command no Mac, .bat no Windows). (" .. tostring(err) .. ")") end
    failed = true; status = "painel offline"
  end
  return ok
end

-- ---------- leitura ----------
local function r8(a) return emu:read8(a) end
local function dex(internal) return TO_DEX[internal] or 0 end
local function popcount(a, n) local c = 0 for i = 0, n - 1 do local b = r8(a + i) while b > 0 do c = c + (b & 1); b = b >> 1 end end return c end

local function detect()
  local t = ""
  for i = 0x134, 0x143 do local c = r8(i); if c == 0 then break end; t = t .. string.char(c) end
  if t:find("YELLOW") then A, GAME = ADDR.Y, "Yellow"
  elseif t:find("RED") then A, GAME = ADDR.RB, "Red"
  elseif t:find("BLUE") then A, GAME = ADDR.RB, "Blue"
  else A, GAME = nil, t end
  console:log("Jogo: " .. GAME)
end

local function read()
  local s = {map = r8(A.curMap), battle = r8(A.inBattle), btype = r8(A.battleType),
             enemy = dex(r8(A.enemySp)), enemyLv = r8(A.enemyLv),
             pc = r8(A.partyCount), box = r8(A.boxCount), owned = popcount(A.owned, 19), lucky = r8(A.lucky), party = {},
             id = r8(A.playerID) * 256 + r8(A.playerID + 1),
             pt = r8(A.ptH) * 3600 + r8(A.ptM) * 60 + r8(A.ptS)}
  if s.pc > 6 then return nil end
  for i = 0, s.pc - 1 do
    local lv = r8(A.partyLv1 + i * PARTY_MON_SIZE)
    if lv == 0 then return nil end            -- Pokémon entrando no time: espera o próximo quadro
    local nk = {}                              -- apelido: 11 bytes no charset da Gen 1, o painel decodifica
    for j = 0, 10 do local c = r8(A.partyNick + i * 11 + j); nk[#nk + 1] = string.format("%02x", c); if c == 0x50 then break end end
    s.party[#s.party + 1] = {dex = dex(r8(A.partySp + i)), lv = lv, nk = table.concat(nk)}
  end
  return s
end

local function key(s)
  local p = {} for i, m in ipairs(s.party) do p[i] = m.dex .. ":" .. m.lv end
  return table.concat({s.map, s.battle, s.btype, s.enemy, s.pc, s.box, s.owned, s.lucky, table.concat(p, ",")}, "|")
end

-- ---------- lógica ----------
local cand, candKey, stable, lastSent = nil, nil, nil, 0
local lastWild = nil            -- {dex, quando}
local frame = 0
local lastPT, lastID = nil, nil    -- tempo de jogo e ID do treinador da última leitura

local function events(old, new)
  local ev = {}
  -- encontro selvagem (tipo 1 = tutorial do velhinho em Viridian, não conta)
  if old.battle == 0 and new.battle == 1 and new.btype ~= 1 then
    ev[#ev + 1] = {tipo = "encontro", dex = new.enemy, nivel = new.enemyLv}
  end
  if new.battle == 1 and new.enemy > 0 then lastWild = {dex = new.enemy, f = frame} end
  -- Pokémon novo (time + box cresceu)
  local before, after = old.pc + old.box, new.pc + new.box
  if after > before then
    local sp = 0
    if new.pc > old.pc then sp = new.party[new.pc].dex
    elseif lastWild and frame - lastWild.f < 60 * 20 then sp = lastWild.dex end
    local veio = (lastWild and frame - lastWild.f < 60 * 20 and sp == lastWild.dex) and "captura" or "presente/troca"
    ev[#ev + 1] = {tipo = "novo", dex = sp, origem = veio}
  end
  -- evolução: mesmo tamanho de time, um slot mudou de espécie e o nível não caiu
  if new.pc == old.pc and new.box == old.box then
    for i = 1, new.pc do
      local a, b = old.party[i], new.party[i]
      if a and b and a.dex ~= b.dex and b.lv >= a.lv then
        local swapped = false
        for j = 1, old.pc do if old.party[j].dex == b.dex and old.party[j].lv == b.lv then swapped = true end end
        if not swapped then ev[#ev + 1] = {tipo = "evolucao", de = a.dex, dex = b.dex} end
      end
    end
  end
  return ev
end

-- box aberta no PC (só ela fica na memória; as outras o painel lê do .sav)
local function caixa()
  local n = r8(A.boxCount)
  if n > 20 then return nil end
  local sp, nk, lv = {}, {}, {}
  for i = 0, n - 1 do
    sp[#sp + 1] = dex(r8(A.boxSp + i))
    lv[#lv + 1] = r8(A.boxMons + i * 33 + 3)
    local b = {}
    for j = 0, 10 do local c = r8(A.boxNick + i * 11 + j); b[#b + 1] = string.format("%02x", c); if c == 0x50 then break end end
    nk[#nk + 1] = table.concat(b)
  end
  return {num = (r8(A.curBox) & 0x7F) + 1, sp = sp, nk = nk, lv = lv}
end

local function send(s, ev)
  local payload = {jogo = GAME, mapa = s.map, batalha = s.battle, tipo_batalha = s.btype,
                   inimigo = s.enemy, time = s.party, box = s.box, pokedex = s.owned,
                   sortuda = (s.map == GAME_CORNER) and s.lucky or -1, eventos = ev, caixa = caixa()}
  post("/g1/emu", payload)
end

local function show(s)
  buf:clear()
  buf:print("Missão Living Dex · " .. GAME .. " · " .. status .. "\n\n")
  if not s then buf:print("Lendo…\n") return end
  buf:print("Mapa " .. s.map .. " · " .. (s.battle == 1 and "batalha selvagem" or s.battle == 2 and "batalha de treinador" or "andando") .. "\n")
  buf:print("Time: " .. #s.party .. " · Box: " .. s.box .. " · Pokédex: " .. s.owned .. "\n")
  buf:print("\nDeixe esta janela aberta durante a live.\n")
end

callbacks:add("start", detect)
callbacks:add("reset", function() detect(); stable, cand, candKey, lastPT, lastID, lastWild = nil, nil, nil, nil, nil, nil end)
callbacks:add("frame", function()
  frame = frame + 1
  if frame % 15 ~= 0 then return end         -- 4 leituras por segundo
  if not A then detect(); if not A then return end end
  local ok, err = pcall(function()
    local s = read()
    if not s then return end
    -- Carregou save, save state ou trocou de jogo: o tempo de jogo voltou ou pulou, ou o ID do treinador mudou.
    -- Nesse caso só refaz a base, sem gerar captura/evolução falsa.
    local pulou = lastPT and (s.id ~= lastID or s.pt < lastPT or s.pt - lastPT > 3)
    lastPT, lastID = s.pt, s.id
    if pulou then stable, cand, candKey = nil, nil, nil; lastWild = nil; console:log("Save carregado: base refeita") return end
    local k = key(s)
    if k ~= candKey then cand, candKey = s, k; return end   -- precisa repetir igual na leitura seguinte
    if not stable then stable = s; send(s, {}); show(s); return end
    if k ~= key(stable) then
      local ev = events(stable, s)
      stable = s; send(s, ev); show(s); lastSent = frame
    elseif frame - lastSent > 60 * 10 then             -- a cada 10 s confirma que está vivo
      send(s, {}); show(s); lastSent = frame
    end
  end)
  if not ok then console:log("erro: " .. tostring(err)) end
end)
if emu then detect() end
console:log("Missão Gen 1 carregado. Deixe o painel aberto.")
