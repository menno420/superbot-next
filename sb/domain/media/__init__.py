"""Shared media ingestion (band 7) — the video knowledge tasks onto K10.

Module map:
  video.py     URL extraction + sanitisation + fact rendering (shipped
               youtube_context_service semantics) over an INSTALLABLE
               metadata reader port (the network fetch + cache is the
               named successor port — D-0047)
  ai_tasks.py  K10 registrations: video.describe / video.compare /
               video.qa claimed byte-identical; the video-URL route
               probe; the gatherer with the empty-facts short-circuit;
               the deterministic refusal floor + task contract
"""
