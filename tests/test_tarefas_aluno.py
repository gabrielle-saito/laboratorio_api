"""TAREFA DO ALUNO -- os cinco testes que faltam para os >= 8 do entregavel.

Cada teste abaixo tem nome, docstring e um pytest.skip. Apague o skip, escreva o
corpo, e o teste passa a valer. Nenhum deles precisa de banco: os tres primeiros
rodam so contra o motor.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from app.dominio.motor_emergia import SEIS_CASAS, calcular_indices
from app.dominio.tipos import CategoriaFluxo, FluxoEmergetico


def test_regressao_numerica_contra_a_planilha(fluxos_golden):
    """Compara os seis indices com a aba SSB da Planilha_base.xlsx.

    Criterio do entregavel: abs(delta) <= 1E-6 por indice. Comece pelo inventario
    de referencia (Y = 200, F = 50, renovaveis = 115, nao renovaveis = 85) e
    escreva os seis valores esperados a mao antes de rodar -- se o teste passar
    de primeira sem voce saber o valor esperado, ele nao esta provando nada.
    """
    # Derivados a mao ANTES de rodar, a partir de Y = 200, F = 50, R' = 115, N' = 85:
    #   EYR = Y / F        = 200 / 50                = 4
    #   ELR = N' / R'      = 85 / 115                = 0,739130434...  -> 0,739130
    #   ESI = EYR / ELR    = 4 * 115 / 85 = 460 / 85 = 5,411764705...  -> 5,411765
    #   EII = ELR / EYR    = 85 / 460                = 0,184782608...  -> 0,184783
    #   %R  = R' / Y * 100 = 115 / 200 * 100         = 57,5
    esperado = {
        "y": Decimal("200"),
        "eyr": Decimal("4"),
        "elr": Decimal("0.739130"),
        "esi": Decimal("5.411765"),
        "eii": Decimal("0.184783"),
        "percentual_r": Decimal("57.5"),
    }
    indices = calcular_indices(fluxos_golden, Decimal("1000"))
    for nome, valor in esperado.items():
        obtido = getattr(indices, nome)
        assert abs(obtido - valor) <= SEIS_CASAS, f"{nome}: esperado {valor}, obtido {obtido}"


def test_quantizacao_unica_no_final():
    """Mostra o erro duplo de arredondar no meio do calculo.

    Calcule ESI = EYR / ELR de duas formas: (a) quantizando EYR e ELR para seis
    casas antes de dividir; (b) dividindo em 28 digitos e quantizando so o ESI.
    Os dois resultados diferem -- e o motor usa (b). Prove a diferenca.
    """
    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_EVEN
        eyr = Decimal("200") / Decimal("50")        # 4
        elr = Decimal("85") / Decimal("115")        # 0,7391304347826086956521739130

        # (a) quantiza EYR e ELR para seis casas ANTES de dividir: ELR vira 0,739130
        #     e o erro de 4,3E-7 do ELR e amplificado pela divisao (~7x).
        esi_a = (eyr.quantize(SEIS_CASAS) / elr.quantize(SEIS_CASAS)).quantize(SEIS_CASAS)
        # (b) divide em 28 digitos e quantiza so o resultado: o que o motor faz.
        esi_b = (eyr / elr).quantize(SEIS_CASAS)

    assert esi_b == Decimal("5.411765")     # 460 / 85 = 5,41176470588...
    assert esi_a == Decimal("5.411768")     # erro duplo: 3E-6, tres vezes a tolerancia
    assert abs(esi_a - esi_b) > SEIS_CASAS  # estoura o criterio de 1E-6 por indice

    # E o motor segue (b), nao (a):
    fluxos = [FluxoEmergetico(r, c, Decimal(v)) for r, c, v in [
        ("chuva", CategoriaFluxo.R, "100"), ("solo", CategoriaFluxo.N, "50"),
        ("fertilizante", CategoriaFluxo.MR, "10"), ("diesel", CategoriaFluxo.MN, "20"),
        ("mao_de_obra", CategoriaFluxo.SR, "5"), ("frete", CategoriaFluxo.SN, "15")]]
    assert calcular_indices(fluxos, Decimal("1000")).esi == esi_b


def test_ordem_da_soma_com_magnitudes_divergentes():
    """A associatividade quebra quando as magnitudes divergem.

    Monte um inventario com um fluxo de 1E20 sej e outro de 1E-5 sej e some nas
    duas ordens possiveis. Explique, no corpo do teste, por que a precisao de 28
    digitos e o limite -- e por que ordenar o inventario e uma decisao de dominio.
    """
    # O docstring sugere 1E20 e 1E-5, mas esse par CABE em 28 digitos (21 inteiros +
    # 5 decimais = 26) e nao perde nada. O limite so aparece quando a soma pede mais
    # de 28 digitos significativos: com 1E21 (22 digitos inteiros) sobram 6 casas,
    # e 4E-7 ja e menos que meio ulp (5E-7).
    #   grande primeiro:   1E21 + 4E-7 -> 1E21 (4E-7 e absorvido), de novo -> 1E21
    #   pequenos primeiro: 4E-7 + 4E-7 = 8E-7, e so entao 1E21 + 8E-7 -> 1E21 + 1E-6
    # Cada soma individual e correta; o que quebra e a associatividade.
    # N e MN (1E11) existem so para ELR e EYR ficarem definidos e o quantize caber.
    def inventario(renovaveis: list[str]) -> list[FluxoEmergetico]:
        return ([FluxoEmergetico(f"r{i}", CategoriaFluxo.R, Decimal(v))
                 for i, v in enumerate(renovaveis)]
                + [FluxoEmergetico("n", CategoriaFluxo.N, Decimal("1E11")),
                   FluxoEmergetico("d", CategoriaFluxo.MN, Decimal("1E11"))])

    grande_primeiro = calcular_indices(inventario(["1E21", "4E-7", "4E-7"]), Decimal("1000"))
    pequenos_primeiro = calcular_indices(inventario(["4E-7", "4E-7", "1E21"]), Decimal("1000"))

    assert pequenos_primeiro.y - grande_primeiro.y == SEIS_CASAS
    assert grande_primeiro != pequenos_primeiro

    # Consequencia de dominio: o motor NAO e invariante a permutacao quando as
    # magnitudes passam de 28 digitos. Hoje nada ordena o inventario; se o dado
    # real chegar a esse extremo, ordenar (ex.: do menor para o maior) deixa de ser
    # detalhe de implementacao e vira regra de dominio, que precisa de dono e de teste.


def test_erro_de_dominio_responde_problem_json(cliente, corpo_golden):
    """Inventario sem fluxo renovavel deve sair 422 em application/problem+json.

    Hoje sai 500, porque o handler de FluxosInsuficientes nao existe -- note que
    o 404 e o 422 do framework JA saem no formato certo, pelos handlers do
    esqueleto: o que falta e so o erro de dominio. Feche o TODO PASSO 3 em
    app/main.py e depois assegure aqui: status 422, header content-type
    application/problem+json e os cinco campos da RFC 9457.
    """
    # so N e MN: nenhum fluxo renovavel, ELR indefinido -> FluxosInsuficientes
    corpo_golden["fluxos"] = [f for f in corpo_golden["fluxos"]
                              if f["categoria"] in ("N", "MN")]
    r = cliente.post("/v1/safras/42/calculos", json=corpo_golden)

    assert r.status_code == 422
    assert r.headers["content-type"].startswith("application/problem+json")
    corpo = r.json()
    for campo in ("type", "title", "status", "detail", "instance"):
        assert campo in corpo
    assert corpo["status"] == 422
    assert corpo["type"].endswith("/fluxos-insuficientes")


def test_campo_extra_no_corpo_da_requisicao_e_rejeitado(cliente, corpo_golden):
    """"energia_produto_jj" tem de morrer com 422, nao virar calculo incompleto.

    Hoje o CalculoRequestDTO nao declara extra="forbid": o campo desconhecido e
    ignorado e o typo passa silencioso, exatamente como na planilha. Feche o
    TODO PASSO 3 em app/api/v1/dto.py e prove aqui.
    """
    corpo_golden["energia_produto_jj"] = "1000"      # typo, alem do campo correto
    r = cliente.post("/v1/safras/42/calculos", json=corpo_golden)

    assert r.status_code == 422
    assert r.headers["content-type"].startswith("application/problem+json")
    assert any(e["campo"] == "body.energia_produto_jj" for e in r.json()["erros"])

    # o typo no lugar do campo correto tambem morre (nao vira calculo incompleto)
    del corpo_golden["energia_produto_j"]
    assert cliente.post("/v1/safras/42/calculos", json=corpo_golden).status_code == 422
