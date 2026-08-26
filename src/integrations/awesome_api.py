import os
import httpx
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
from src.schemas.quote_schema import Quote


ENV_PATH = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=ENV_PATH)

AWESOME_API_URL = os.getenv(
    'AWESOME_API_URL',
    'https://economia.awesomeapi.com.br'
)
AWESOME_API_TOKEN = os.getenv('AWESOME_API_TOKEN')
AWESOME_API_TIMEOUT = float(os.getenv('AWESOME_API_TIMEOUT', '10'))


class AwesomeAPIError(Exception):
    """Erro de comunicação com a AwesomeAPI."""


def _build_client() -> httpx.AsyncClient:
    headers = {'Accept': 'application/json'}

    if AWESOME_API_TOKEN:
        headers['Authorization'] = f'Bearer {AWESOME_API_TOKEN}'

    return httpx.AsyncClient(
        base_url=AWESOME_API_URL,
        headers=headers,
        timeout=AWESOME_API_TIMEOUT
    )


async def _request(path: str) -> dict | list:
    try:
        async with _build_client() as client:
            response = await client.get(path)
            response.raise_for_status()

            return response.json()

    except httpx.HTTPStatusError as error:
        raise AwesomeAPIError(
            f'AwesomeAPI returned status '
            f'{error.response.status_code} for {path}'
        ) from error

    except httpx.HTTPError as error:
        raise AwesomeAPIError(
            f'Failed to reach AwesomeAPI: {error}'
        ) from error

    except ValueError as error:
        raise AwesomeAPIError(
            f'Invalid JSON returned by AwesomeAPI: {error}'
        ) from error


def _normalize_pair(pair: str) -> str:
    normalized = pair.strip().upper().replace('/', '-')

    if '-' not in normalized:
        raise ValueError(
            f'Invalid coin pair: {pair}. Expected format "USD-BRL"'
        )

    return normalized


async def get_last_quotes(pairs: list[str]) -> dict[str, Quote]:
    """Consulta a cotação mais recente de um ou mais pares.

    Recebe pares no formato "USD-BRL" e devolve um dicionário
    indexado pelo par informado.
    """
    if not pairs:
        raise ValueError('At least one coin pair is required')

    normalized = [_normalize_pair(pair) for pair in pairs]

    payload = await _request(f'/json/last/{",".join(normalized)}')

    quotes: dict[str, Quote] = {}

    for pair in normalized:
        raw = payload.get(pair.replace('-', ''))

        if raw is None:
            raise AwesomeAPIError(f'Quote not found for pair {pair}')

        quotes[pair] = Quote.model_validate(raw)

    return quotes


async def get_last_quote(origin: str, target: str) -> Quote:
    """Consulta a cotação mais recente de um único par de moedas."""
    pair = _normalize_pair(f'{origin}-{target}')

    quotes = await get_last_quotes([pair])

    return quotes[pair]


# O endpoint /json/daily devolve no máximo 360 fechamentos por requisição.
MAX_HISTORY_DAYS = 360


def _parse_history(pair: str, payload: dict | list) -> list[Quote]:
    # Quando não há cotação no período a API responde com um objeto de erro
    # ao invés da lista de fechamentos.
    if not isinstance(payload, list):
        return []

    code, codein = pair.split('-')

    history: list[Quote] = []

    for item in payload:
        quote = Quote.model_validate(item)

        # O histórico só traz code/codein no primeiro item da lista.
        quote.code = quote.code or code
        quote.codein = quote.codein or codein

        history.append(quote)

    return history


async def get_quote_history(
    origin: str,
    target: str,
    days: int = 30
) -> list[Quote]:
    """Consulta o histórico de fechamento de um par de moedas."""
    pair = _normalize_pair(f'{origin}-{target}')

    if days < 1:
        raise ValueError('days must be greater than zero')

    payload = await _request(f'/json/daily/{pair}/{days}')

    return _parse_history(pair, payload)


async def get_quote_history_range(
    origin: str,
    target: str,
    start_date: date,
    end_date: date
) -> list[Quote]:
    """Consulta o histórico de fechamento dentro de um intervalo de datas.

    A AwesomeAPI limita a resposta a `MAX_HISTORY_DAYS` fechamentos por
    requisição, então intervalos maiores devem ser paginados pelo chamador.
    """
    pair = _normalize_pair(f'{origin}-{target}')

    if start_date > end_date:
        raise ValueError('start_date must not be after end_date')

    payload = await _request(
        f'/json/daily/{pair}/{MAX_HISTORY_DAYS}'
        f'?start_date={start_date:%Y%m%d}&end_date={end_date:%Y%m%d}'
    )

    return _parse_history(pair, payload)


async def get_available_pairs() -> dict[str, str]:
    """Lista os pares de moedas suportados pela AwesomeAPI."""
    return await _request('/json/available')
