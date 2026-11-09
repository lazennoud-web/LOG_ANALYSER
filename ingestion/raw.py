import gzip
import os
from pathlib import Path
from log_config import get_logger

logger = get_logger('ingestion')

"""
    Read from data all files
    in : data [directory]
    out : list of rows
"""
DATA_DIR = Path(__file__).resolve().parent.parent / 'data'


def to_rows(path: str = DATA_DIR):
    data_dir = Path(path)
    rows = []
    try:
        #du plus ancien (auth.log.4.gz) au plus recent (auth.log.1)
        files = sorted(os.listdir(data_dir), reverse=True)
    except FileNotFoundError as exc:
        logger.error(f'Dossier de logs introuvable : {data_dir} ({exc})')
        return rows
    for file in files:
        file_path = data_dir / file
        try:
            open_type = gzip.open(file_path, mode='rt') if file.endswith('.gz') else open(file_path, encoding='utf-8', errors='replace')
            with open_type as f:
                rows.extend(f.readlines())
        except OSError as exc:
            logger.warning(f'Impossible de lire {file_path} : {exc}')
    return rows


if __name__ == '__main__':
    data = to_rows()
    if data:
        print(len(data))
        print(data[:10])
