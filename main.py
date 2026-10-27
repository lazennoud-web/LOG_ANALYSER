#connection echoué par pays et par mois 
#nbre d'echoue par jours si possible une courbe
from ingestion import raw
from processing import extract_transforme

if __name__ == "__main__":
    data=raw.to_rows('./data')

if data :
    extract_transforme.exctract_from_row(data[111])
