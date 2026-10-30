import requests
from bs4 import BeautifulSoup
import boto3
import uuid

def lambda_handler(event, context):
    url = "https://ultimosismo.igp.gob.pe/productos/reportes-sismicos"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers, timeout=20)
    if response.status_code != 200:
        return {
            'statusCode': response.status_code,
            'body': 'Error al acceder a la pagina del IGP'
        }

    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table')
    if not table:
        return {
            'statusCode': 404,
            'body': 'No se encontro la tabla en la pagina del IGP'
        }

    headers_tabla = [th.get_text(strip=True) for th in table.find_all('th')]

    filas = []
    for tr in table.find_all('tr')[1:]:
        celdas = tr.find_all('td')
        if not celdas:
            continue
        fila = {}
        for i, celda in enumerate(celdas):
            clave = headers_tabla[i] if i < len(headers_tabla) else f"col{i}"
            fila[clave] = celda.get_text(strip=True)
        filas.append(fila)
        if len(filas) == 10:
            break

    dynamodb = boto3.resource('dynamodb')
    tabla = dynamodb.Table('TablaSismosIGP')

    scan = tabla.scan()
    with tabla.batch_writer() as batch:
        for item in scan['Items']:
            batch.delete_item(Key={'id': item['id']})

    for i, fila in enumerate(filas, start=1):
        fila['#'] = i
        fila['id'] = str(uuid.uuid4())
        tabla.put_item(Item=fila)

    return {
        'statusCode': 200,
        'body': {
            'cantidad': len(filas),
            'sismos': filas
        }
    }
