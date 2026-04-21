import os
from googleapiclient.discovery import build

YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")

# Use API Key if possible, but the user provided Client ID and Secret.
# For simple search, API Key is usually used. If user provided OAuth2 credentials,
# we can still use them or ask for API Key. Assuming we use an API Key for simplicity if available,
# but I will try to use the credentials if I can.
# Actually, the user provided "secret number" which might be an API Key or Client Secret.
# If it's a Client Secret, it's for OAuth2.
# Let's assume we want a simple search. I'll try to use the secret as an API Key first,
# or just use it in a query if it's meant for that.
# Given the format GOCSPX-..., it looks like a Client Secret.

def search_youtube_videos(query, max_results=5):
    """
    Real-time YouTube search.
    Requires YOUTUBE_API_KEY in .env.
    """
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        # User provided Client Secret but search needs API Key
        api_key = os.getenv("YOUTUBE_CLIENT_SECRET")

    try:
        # If still no key or it is a placeholder
        if not api_key:
            print("[YouTube] MISSING API KEY: Please set YOUTUBE_API_KEY in .env")
            return []

        if api_key.startswith("GOCSPX"):
            print("[YouTube] ERROR: You are using a Client Secret (GOCSPX-...) instead of an API Key!")
            print("[YouTube] To fix: Go to Google Cloud Console -> Credentials -> Create Credentials -> API Key.")
            return []

        youtube = build("youtube", "v3", developerKey=api_key)
        request = youtube.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=max_results
        )
        response = request.execute()
        
        videos = []
        for item in response.get("items", []):
            if "videoId" in item["id"]:
                videos.append({
                    "video_id": item["id"]["videoId"],
                    "title": item["snippet"]["title"],
                    "thumbnail": item["snippet"]["thumbnails"]["default"]["url"],
                    "channel_title": item["snippet"]["channelTitle"],
                    "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
                })
        
        return videos
    except Exception as e:
        error_msg = str(e)
        print(f"[YouTube] API error details: {error_msg}")
        if "API key not valid" in error_msg or "keyInvalid" in error_msg:
            print("[YouTube] ERROR: The provided API key is invalid. Get a 'Data API v3' Key from Google Cloud Console.")
        elif "quotaExceeded" in error_msg.lower():
            print("[YouTube] ERROR: API Quota exceeded. Try again tomorrow or use a different key.")
        return []
