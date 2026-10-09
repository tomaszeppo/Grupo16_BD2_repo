import re
MAPA = dict(ALE='GER',ING='ENG',PAI='NED',DIN='DEN',SER='SRB',AUS='AUT',UCR='UKR',GAL='WAL',ESC='SCO',SUE='SWE',REP='CZE',JAP='JPN',COR='KOR',IRA='IRN',ARA='KSA',AU1='AUS',CAT='QAT',IR1='IRQ',EMI='UAE',NIG='NGA',EGI='EGY',AR1='ALG',CAM='CMR',COS='CIV',SUD='RSA',MAL='MLI',EST='USA',CO1='CRC',NUE='NZL',ESL='SVK')
VIEJOS = '|'.join(MAPA)
def convertir(texto, patron):
    return re.sub(patron, lambda m: m.group(0).replace(m.group(1), MAPA[m.group(1)], 1), texto)
