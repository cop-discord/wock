import requests
token = "MTIwMzQxOTMxNjIzMDQyMjU0OA.G_zm82.whfSqkAe1q188SfM3q_wkDxqq1CcBKcZLhvgXQ"
r = requests.get("https://discord.com/api/v10/users/@me/guilds", headers = {"Authorization": f"Bot {token}"})
print(len(r.json()))