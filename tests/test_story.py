import asyncio
from app.services.story_service import StoryService

async def main():
    print("Testing story generation...")
    story = await StoryService.generate_story("A cat learns to fly", genre="Thriller")
    print(story.title)
    print(f"Characters: {len(story.characters)}")
    print(f"Scenes: {len(story.scenes)}")
    total_words = sum(len(scene.narration.split()) for scene in story.scenes)
    print(f"Total Narration Words: {total_words}")
    for sc in story.scenes:
        print(f"Scene {sc.scene_number} ({len(sc.narration.split())} words): {sc.narration}")
    print("DONE")

asyncio.run(main())
