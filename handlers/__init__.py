from handlers.main_menu import router as main_menu_router
from handlers.search import router as search_router
from handlers.track import router as track_router
from handlers.artist import router as artist_router
from handlers.album import router as album_router
from handlers.favorites import router as favorites_router
from handlers.playlists import router as playlists_router
from handlers.history import router as history_router
from handlers.settings import router as settings_router
from handlers.random_track import router as random_router
from handlers.lyrics import router as lyrics_router

all_routers = [
    main_menu_router,
    search_router,
    track_router,
    artist_router,
    album_router,
    favorites_router,
    playlists_router,
    history_router,
    settings_router,
    random_router,
    lyrics_router,
]
