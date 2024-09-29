import requests
import time

# Riot API Key and Summoner Info
RIOT_API_KEY = 'YourAPIKeyHere'
DISCORD_WEBHOOK_URL = 'YourWebhookURLHere'
ROLE_TO_PING = '<@&YourRoleIDHere>'

# List of summoner names (you can add more accounts here)
SUMMONER_NAMES = [
    'name',  # This will use the default tag EUW
    'name2#customTag',  # This has a specific tag
    'name3#EUW',     # Example with a generic tag
]

# Function to split summoner name into gameName and tagLine (without including the #)
def split_summoner_name(summoner_name):
    if '#' in summoner_name:
        game_name, tag_line = summoner_name.split('#', 1)  # Split into two parts at the first occurrence of #
    else:
        game_name = summoner_name
        tag_line = 'EUW'  # Default tagLine if no # is provided
        print(f"No tag provided for {game_name}. Using default tag: {tag_line}")  # Output the default tag
    return game_name, tag_line

# Get Summoner ID based on summoner name using Riot Account API
def get_summoner_puuid(game_name, tag_line):
    url = f'https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}'
    headers = {'X-Riot-Token': RIOT_API_KEY}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get('puuid')  # Use 'puuid' as the identifier in Riot's ecosystem
    elif response.status_code == 429:  # Rate limit exceeded
        print("Rate limit exceeded. Retrying in 60 seconds...")
        time.sleep(60)  # Wait before retrying
        return get_summoner_puuid(game_name, tag_line)  # Retry
    else:
        print(f"Error fetching summoner ID for {game_name}#{tag_line}: {response.status_code}")
        return None

# Check if the player is currently in a game using Summoner PUUID
def is_player_in_game(summoner_puuid):
    url = f'https://euw1.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{summoner_puuid}'
    headers = {'X-Riot-Token': RIOT_API_KEY}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return True
    elif response.status_code == 404:
        return False  # Not in a game
    elif response.status_code == 429:  # Rate limit exceeded
        print("Rate limit exceeded. Retrying in 60 seconds...")
        time.sleep(60)
        return is_player_in_game(summoner_puuid)  # Retry
    else:
        print(f"Error checking if player is in-game: {response.status_code}")
        return False

# Send message to Discord channel via Webhook
def send_webhook_message(message):
    data = {
        "content": message,
        "username": "LoL Game Notifier"  # You can set a custom name for the webhook
    }
    response = requests.post(DISCORD_WEBHOOK_URL, json=data)
    
    if response.status_code == 204:
        print("Notification sent to Discord")
    else:
        print(f"Failed to send webhook message: {response.status_code}")

# Main function to check multiple player statuses and send notifications
def notify_users():
    user_states = {}  # Dictionary to track game status of each summoner
    
    # Initialize state for each summoner
    for summoner_name in SUMMONER_NAMES:
        game_name, tag_line = split_summoner_name(summoner_name)
        summoner_puuid = get_summoner_puuid(game_name, tag_line)  # 'puuid' is the player's universal ID
        if summoner_puuid is not None:
            user_states[summoner_name] = {
                'puuid': summoner_puuid,
                'in_game_last_check': False,  # Track if the player was in-game in the previous check
                'tag_line': tag_line
            }
    
    # Continuous loop to monitor all users
    while True:
        for summoner_name, state in user_states.items():
            summoner_puuid = state['puuid']
            tag_line = state['tag_line']
            in_game_last_check = state['in_game_last_check']
            
            in_game = is_player_in_game(summoner_puuid)
            
            if in_game and not in_game_last_check:
                # Player has just entered a new game
                summoner_name_encoded = summoner_name.replace(" ", "%20")  # Replace spaces with %20 for URL encoding
                
                # Construct the message
                message = f"{summoner_name.split('#')[0]} is currently in a new game! "
                
                if '#' in summoner_name:
                    # If tag is provided, use it only once after the dash in the URL
                    message += f"https://www.op.gg/summoners/euw/{summoner_name_encoded.split('#')[0]}-{tag_line} {ROLE_TO_PING}"
                else:
                    # If no specific tag is provided, include the default tag in the URL
                    message += f"https://www.op.gg/summoners/euw/{summoner_name_encoded}-{tag_line} {ROLE_TO_PING}"

                send_webhook_message(message)
                print(message)
            
            elif not in_game and in_game_last_check:
                # Player has exited the game
                print(f"{summoner_name}#{tag_line} has left the game.")
            
            # Update the previous status
            user_states[summoner_name]['in_game_last_check'] = in_game
        
        # Check every minute for all summoners
        time.sleep(60)

# Start the notification process for multiple users
if __name__ == '__main__':
    notify_users()
