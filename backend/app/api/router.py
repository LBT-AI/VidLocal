from fastapi import APIRouter
from app.api import projects, subtitles, tts, publish, connect, jobs, facebook_to_youtube, glossary, video_jobs

api_router = APIRouter()
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(subtitles.router, prefix="/projects", tags=["subtitles"])
api_router.include_router(tts.router, prefix="/projects", tags=["tts"])
api_router.include_router(publish.router, prefix="/projects", tags=["publish"])
api_router.include_router(connect.router, prefix="/connect", tags=["connect"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(facebook_to_youtube.router, prefix="/facebook-to-youtube", tags=["facebook-to-youtube"])
api_router.include_router(glossary.router, prefix="/glossary", tags=["glossary"])
api_router.include_router(video_jobs.router, prefix="/video-jobs", tags=["video-jobs"])
