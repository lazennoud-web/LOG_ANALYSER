import logging
from pathlib import Path

"""
    Configuration des logs du projet
    in : nom du module (ex : "serving")
    out : logger qui écrit dans logs/<nom>.log (+ console pour les warnings et erreurs)
"""
LOG_DIR = Path(__file__).resolve().parent / 'logs'

def get_logger(name:str)->logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:#déjà configuré : on n'ajoute pas les handlers deux fois
        return logger
    logger.setLevel(logging.DEBUG)
    LOG_DIR.mkdir(exist_ok=True)
    logger_format = logging.Formatter(fmt='%(asctime)s|%(levelname)s|%(name)s|%(message)s',
                                      datefmt='%d-%m-%Y %H:%M:%S')
    file = logging.FileHandler(LOG_DIR / f'{name}.log', encoding='utf-8')
    file.setFormatter(logger_format)
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(logger_format)
    logger.addHandler(file)
    logger.addHandler(console)
    return logger

if __name__ == '__main__':
    logger = get_logger('test')
    logger.info('From logger Info Msg')
    logger.error('From logger Error Msg')
