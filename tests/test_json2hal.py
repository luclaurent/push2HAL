import os
from push2HAL import execHAL


def test_runJSON2HAL():
    res = execHAL.runJSON2HAL(
        jsonContent="examples/test.json",
        verbose=False,
        prod="preprod",
        credentials=None,
        completion=None,
        idhal=None,
    )
    assert res == os.EX_CONFIG
