import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from dotenv import load_dotenv
from config import DATA_DIR

load_dotenv()

print('Loading data...')
daily = pd.read_parquet(f'{DATA_DIR}/dash_daily.parquet')
brackets = pd.read_parquet(f'{DATA_DIR}/dash_brackets.parquet')
top_products = pd.read_parquet(f'{DATA_DIR}/dash_top_products.parquet')
reviews_sample = pd.read_parquet(f'{DATA_DIR}/dash_reviews.parquet')
df_emb = pd.read_parquet(f'{DATA_DIR}/electronics_emb.parquet')
index = faiss.read_index(f'{DATA_DIR}/electronics.faiss')
print(f'Loaded {len(df_emb):,} reviews, {index.ntotal:,} vectors')

model = SentenceTransformer('all-MiniLM-L6-v2')
client = OpenAI()

# summary stats
TOTAL_REVIEWS = len(df_emb)
AVG_RATING = float(df_emb['rating'].mean())
POS_PCT = (df_emb['sentiment']=='pos').mean() * 100
NEG_PCT = (df_emb['sentiment']=='neg').mean() * 100
UNIQUE_PRODUCTS = df_emb['product_title'].nunique()