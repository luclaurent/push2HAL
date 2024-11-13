import os
from push2HAL import libHAL

def test_doiInHAL():
    api = libHAL.APIHAL()
    res = api.checkDoiInHAL('10.1007/s11831-017-9226-3')
    assert res == True
    
def test_doiNotInHAL():
    res = libHAL.checkDoiInHAL('10.1007/XXXX')
    assert res == False