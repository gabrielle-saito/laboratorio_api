"""PASSO 4 do laboratorio: a rota-armadilha.

Higiene: apague este arquivo ao final da aula, ou mantenha-o num branch de
demonstracao. Codigo que ensina errado nao fica em main.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter

router = APIRouter(prefix="/v1/demo", tags=["armadilha"])


@router.get("/travada")
async def travada():
    # await devolve o event loop durante a espera: as outras requisicoes seguem
    await asyncio.sleep(10)
    return {"ok": True}
