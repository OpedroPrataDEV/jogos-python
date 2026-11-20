"""Progresso do jogador (minério + melhorias) e ranking, salvos em JSON na pasta 'dados'."""
import copy
import json
import os
import time

import config as C

ARQ_PROGRESSO = os.path.join(C.DADOS, "progresso.json")
ARQ_RANKING = os.path.join(C.DADOS, "ranking.json")

PROGRESSO_PADRAO = {
    "minerio": 0,
    "melhorias": {"tungstenio": 0, "plataforma": 0, "capacete": 0, "ima": 0, "isolamento": 0},
    "fase_max": 1,        # maior fase desbloqueada (1..5)
    "recorde": 0,
    "partidas": 0,
    "zerado": False,
}

RANKING_PADRAO = [
    {"nome": "PIP", "pontos": 7400, "fase": 5, "data": "--/--"},
    {"nome": "ROCHA", "pontos": 5200, "fase": 4, "data": "--/--"},
    {"nome": "DIAMANTE", "pontos": 3600, "fase": 3, "data": "--/--"},
    {"nome": "BROCA", "pontos": 2300, "fase": 2, "data": "--/--"},
    {"nome": "MINEIRO", "pontos": 1200, "fase": 2, "data": "--/--"},
]


def _ler(caminho, padrao):
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return copy.deepcopy(padrao)


def _gravar(caminho, dados):
    try:
        os.makedirs(C.DADOS, exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
    except OSError:
        pass  # sem permissão de escrita: o jogo continua normalmente


def carregar_progresso():
    dados = _ler(ARQ_PROGRESSO, PROGRESSO_PADRAO)
    base = copy.deepcopy(PROGRESSO_PADRAO)
    for k, v in dados.items():
        if k == "melhorias" and isinstance(v, dict):
            base["melhorias"].update({m: int(n) for m, n in v.items() if m in base["melhorias"]})
        elif k in base:
            base[k] = v
    return base


def salvar_progresso(p):
    _gravar(ARQ_PROGRESSO, p)


def carregar_ranking():
    r = _ler(ARQ_RANKING, RANKING_PADRAO)
    if not isinstance(r, list) or not r:
        r = copy.deepcopy(RANKING_PADRAO)
    return sorted(r, key=lambda e: -int(e.get("pontos", 0)))[:10]


def qualifica(pontos):
    r = carregar_ranking()
    return pontos > 0 and (len(r) < 10 or pontos > int(r[-1]["pontos"]))


def inserir_ranking(nome, pontos, fase):
    r = carregar_ranking()
    nome = (nome.strip() or "ANONIMO")[:8].upper()
    entrada = {"nome": nome, "pontos": int(pontos), "fase": int(fase), "data": time.strftime("%d/%m")}
    r.append(entrada)
    r.sort(key=lambda e: -int(e["pontos"]))
    r = r[:10]
    _gravar(ARQ_RANKING, r)
    return r.index(entrada) if entrada in r else -1
