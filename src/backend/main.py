import pandas as pd

# Read the watched.csv file
def watched_db():
    try:
        watched = pd.read_csv('data/watched.csv')
        return watched
    except FileNotFoundError:
        print("ERROR: Could not find 'data/watched.csv'.")
        print("Make sure your Letterboxd file is inside the src/backend/data/ folder.")
        return None
    
# Read the ratings.csv file
def ratings_db():
    try:
        ratings = pd.read_csv('data/ratings.csv')
        return ratings
    except FileNotFoundError:
        print("ERROR: Could not find 'data/ratings.csv'.")
        print("Make sure your Letterboxd file is inside the src/backend/data/ folder.")
        return None

# Read the diary.csv file
def diary_db():
    try:
        diary = pd.read_csv('data/diary.csv')
        return diary
    except FileNotFoundError:
        print("ERROR: Could not find 'data/diary.csv'.")
        print("Make sure your Letterboxd file is inside the src/backend/data/ folder.")
        return None

# Filter movies by decades
def movies_decades(watched):
    watched['Decade'] = (watched['Year'] // 10) * 10
    
    decadeCounts = watched['Decade'].value_counts()
    topDecade = decadeCounts.idxmax()
    topCount = decadeCounts.max()

    return topCount, topDecade

# User Average Rating
def average_rating(ratings):
    avgRating = ratings['Rating'].mean()
    return round(avgRating, 2)

# Day of the week with most watched movies
def day_of_the_week(diary):
    diary['Watched Date'] = pd.to_datetime(diary['Watched Date'])
    diary['Day'] = diary['Watched Date'].dt.day_name()
    
    dayCounts = diary['Day'].value_counts()
    topDay = dayCounts.idxmax()

    return topDay

# Oldest and Newest movie year watched
def time_machine(watched):
    oldestYear = watched['Year'].min()
    newestYear = watched['Year'].max()

    return oldestYear, newestYear


# Print stats
def print_movie_stats(stats):
    print(f"You have watched a total of {stats['totalMovies']} movies.")
    print(f"Your Most Watched Decade is {stats['topDecade']}. ({stats['topCount']} movies)")
    print(f"Your average rating is {stats['avgRating']} stars.")
    print(f"Your most active day is {stats['topDay']}")
    print(f"Oldest year {stats['oldestYear']}. Newest year {stats['newestYear']}")

# Main
if __name__ == "__main__":
    watched_df = watched_db()
    ratings_df = ratings_db()
    diary_df = diary_db()


    if watched_df  is not None and ratings_df is not None and diary_df is not None:
        topCnt, topDec = movies_decades(watched_df)
        avgRating = average_rating(ratings_df)
        topDay = day_of_the_week(diary_df)
        oldestYear, newestYear = time_machine(watched_df)
        
        statsPayload = {
            "totalMovies": len(watched_df),
            "topDecade": topDec,
            "topCount": topCnt,
            "avgRating": avgRating,
            "topDay": topDay,
            "oldestYear": oldestYear,
            "newestYear": newestYear
        }
        
        print_movie_stats(statsPayload)


    