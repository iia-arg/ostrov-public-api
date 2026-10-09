"""Read and calculate an illustrative plan; never saves or submits."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ostrov_api import Client

def main():
 api=Client()
 example=api.get_examples()['examples'][0]
 print(json.dumps({'illustrative':True,'request':example,'result':api.calculate_quote(**example)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
