import gzip
import os
from pathlib import Path
"""
    Read from data all files
    in : data [directory]
    out : list of rows
"""
DATA_DIR = Path(__file__).resolve().parent.parent / 'data'

def to_rows(path:str=DATA_DIR):
    data_dir=Path(path)
    rows=[]
    try:
        #du plus ancien (auth.log.4.gz) au plus recent (auth.log.1)
        files=sorted(os.listdir(data_dir),reverse=True)
    except FileNotFoundError as e:
        print(e)
        return rows
    for file in files:
        file_path = data_dir / file
        open_type=gzip.open(file_path,mode='rt') if file.endswith('.gz') else open(file_path)
        with open_type as f:
            rows.extend(f.readlines())
    return rows
if __name__=='__main__':
    data = to_rows()
    if data:
        print(len(data))
        print(data[:10])
