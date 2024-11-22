import os
from push2HAL import execHAL


def test_runPDF2HAL():
    res = execHAL.runPDF2HAL(
        pdf_path="examples/file.pdf",
        verbose=False,
        prod="preprod",
        credentials=None,
        completion=None,
        halid=None,
        idhal=None,
        interaction=False,
    )
    assert res == os.EX_CONFIG
