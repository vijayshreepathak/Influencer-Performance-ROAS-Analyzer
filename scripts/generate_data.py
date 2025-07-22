import pandas as pd
import numpy as np
from faker import Faker
import random
from datetime import datetime, timedelta
import os

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)
fake = Faker()

# Output directory
OUTPUT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1. influencers.csv
def generate_influencers(n=50):
    categories = ['Fitness', 'Wellness', 'Nutrition']
    genders = ['Male', 'Female', 'Other']
    platforms = ['Instagram', 'YouTube']
    data = []
    for i in range(1, n+1):
        data.append({
            'influencer_id': i,
            'name': fake.name(),
            'category': random.choice(categories),
            'gender': random.choice(genders),
            'follower_count': random.randint(10_000, 1_000_000),
            'platform': random.choice(platforms)
        })
    return pd.DataFrame(data)

# 2. posts.csv
def generate_posts(influencers, n=200):
    posts = []
    for i in range(1, n+1):
        influencer = influencers.sample(1).iloc[0]
        post_date = fake.date_time_between(start_date='-6M', end_date='now')
        posts.append({
            'post_id': i,
            'influencer_id': influencer['influencer_id'],
            'platform': influencer['platform'],
            'post_date': post_date.strftime('%Y-%m-%d'),
            'post_url': fake.url(),
            'caption': fake.sentence(nb_words=10),
            'reach': random.randint(5000, influencer['follower_count']),
            'likes': random.randint(100, 10000),
            'comments': random.randint(5, 500)
        })
    return pd.DataFrame(posts)

# 3. tracking_data.csv
def generate_tracking_data(influencers, n=5000):
    sources = ['influencer', 'organic', 'paid_ad']
    campaigns = ['MB_SummerSale', 'HKV_ImmunityBoost', 'Gritzo_Growth', 'MB_WinterBlast']
    products = ['MuscleBlaze Whey', 'HKVitals Biotin', 'Gritzo SuperMilk']
    data = []
    for i in range(1, n+1):
        source = random.choices(sources, weights=[0.5, 0.3, 0.2])[0]
        influencer_id = None
        if source == 'influencer':
            influencer_id = int(influencers.sample(1)['influencer_id'])
        campaign = random.choice(campaigns)
        product = random.choice(products)
        transaction_date = fake.date_time_between(start_date='-6M', end_date='now')
        orders = 1 if random.random() < 0.95 else random.randint(2, 5)
        revenue = round(random.uniform(500, 5000) * orders, 2)
        data.append({
            'tracking_id': i,
            'source': source,
            'campaign': campaign,
            'influencer_id': influencer_id,
            'user_id': fake.uuid4(),
            'product': product,
            'transaction_date': transaction_date.strftime('%Y-%m-%d'),
            'orders': orders,
            'revenue': revenue
        })
    return pd.DataFrame(data)

# 4. payouts.csv
def generate_payouts(influencers, posts, tracking_data):
    payouts = []
    for idx, row in influencers.iterrows():
        basis = random.choice(['per_post', 'per_order'])
        if basis == 'per_post':
            rate = round(random.uniform(3000, 10000), 2)
            n_posts = posts[posts['influencer_id'] == row['influencer_id']].shape[0]
            total_payout = rate * n_posts
            payouts.append({
                'payout_id': idx+1,
                'influencer_id': row['influencer_id'],
                'basis': basis,
                'rate': rate,
                'orders': np.nan,
                'total_payout': total_payout
            })
        else:  # per_order
            rate = round(random.uniform(30, 100), 2)
            n_orders = tracking_data[(tracking_data['influencer_id'] == row['influencer_id']) & (tracking_data['source'] == 'influencer')]['orders'].sum()
            total_payout = rate * n_orders
            payouts.append({
                'payout_id': idx+1,
                'influencer_id': row['influencer_id'],
                'basis': basis,
                'rate': rate,
                'orders': n_orders,
                'total_payout': total_payout
            })
    return pd.DataFrame(payouts)

if __name__ == '__main__':
    influencers = generate_influencers()
    posts = generate_posts(influencers)
    tracking_data = generate_tracking_data(influencers)
    payouts = generate_payouts(influencers, posts, tracking_data)

    influencers.to_csv(os.path.join(OUTPUT_DIR, 'influencers.csv'), index=False)
    posts.to_csv(os.path.join(OUTPUT_DIR, 'posts.csv'), index=False)
    tracking_data.to_csv(os.path.join(OUTPUT_DIR, 'tracking_data.csv'), index=False)
    payouts.to_csv(os.path.join(OUTPUT_DIR, 'payouts.csv'), index=False)

    print('Sample data generated and saved to CSV files.')
