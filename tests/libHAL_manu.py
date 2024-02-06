from push2HAL import libHAL

doi = '10.1007/s11831-017-9226-3'
res = libHAL.checkDoiInHAL('10.1007/s11831-017-9226-3')
print('{} in HAL: {}'.format(doi,res))

doi = '10.1007/XXXX'
res = libHAL.checkDoiInHAL('10.1007/XXXX')
print('{} in HAL: {}'.format(doi,res))