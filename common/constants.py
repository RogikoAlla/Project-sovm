"""Game-wide constants for King and Servant."""

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

# King blind-swap privilege limit per round
KING_SWAP_LIMIT: int = 1
