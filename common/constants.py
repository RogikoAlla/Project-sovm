"""Game-wide constants for King and Servant."""

# Network
DEFAULT_HOST: str = "127.0.0.1"
DEFAULT_PORT: int = 65432
BUFFER_SIZE: int = 4096
ENCODING: str = "utf-8"
MSG_SEPARATOR: str = "\n"

# Deck sizes
DECK_36: int = 36
DECK_52: int = 52

# Game
PLAYER_COUNT: int = 4
CARDS_PER_PLAYER_36: int = 9
CARDS_PER_PLAYER_52: int = 13

# Card suits (canonical names)
SUITS: tuple = ("spades", "hearts", "diamonds", "clubs")
SUIT_SYMBOLS: dict = {
    "spades": "\u2660",
    "hearts": "\u2665",
    "diamonds": "\u2666",
    "clubs": "\u2663",
}

# Card ranks
RANKS_36: tuple = ("6", "7", "8", "9", "10", "J", "Q", "K", "A")
RANKS_52: tuple = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")

# King of Spades determines initial King role
KING_OF_SPADES_RANK: str = "K"
KING_OF_SPADES_SUIT: str = "spades"

# Roles
ROLE_KING: str = "King"
ROLE_ACE: str = "Ace"
ROLE_QUEEN: str = "Queen"
ROLE_SERVANT: str = "Servant"

# Counter-clockwise assignment order starting from King of Spades holder
ROLES_CCW: tuple = (ROLE_KING, ROLE_ACE, ROLE_QUEEN, ROLE_SERVANT)

# Clockwise attack order
ATTACK_ORDER: tuple = (ROLE_SERVANT, ROLE_QUEEN, ROLE_ACE, ROLE_KING)

# King blind-swap privilege limit per game session
KING_SWAP_LIMIT: int = 1

# Protocol message types
MSG_THROW: str = "THROW"
MSG_ERROR: str = "ERROR"
MSG_JOIN: str = "JOIN"
MSG_GAME_STATE: str = "GAME_STATE"
MSG_PLAY_CARD: str = "PLAY_CARD"
MSG_ROUND_END: str = "ROUND_END"
MSG_GAME_END: str = "GAME_END"
MSG_SWAP_DECK: str = "SWAP_DECK"
MSG_DONE: str = "DONE"
MSG_DECLARE_TRUMP: str = "DECLARE_TRUMP"
MSG_BEAT: str = "BEAT"
MSG_TAKE: str = "TAKE"
