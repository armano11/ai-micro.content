import asyncio
from pathlib import Path
from typing import List
from app.utils.file_utils import get_project_file_path, get_project_dir
from app.utils.ffmpeg_utils import create_scene_video, concatenate_videos, burn_subtitles_to_video, get_audio_duration
from app.utils.logger import get_logger

logger = get_logger(__name__)

class VideoService:
    @staticmethod
    async def assemble_video(
        project_id: str, 
        image_paths: List[Path], 
        audio_paths: List[Path], 
        srt_path: Path
    ) -> Path:
        """
        Assembles the final video slideshow.
        1. Creates individual MP4 videos for each scene matching its audio duration.
        2. Concatenates them into a single video file.
        3. Burns the master subtitles file onto the concatenated video.
        4. Cleans up temporary video files.
        """
        logger.info(f"Assembling video for project {project_id}...")
        project_dir = get_project_dir(project_id)
        
        # 1. Generate individual scene videos
        scene_video_paths = []
        scene_video_names = []
        tasks = []
        
        for i in range(len(image_paths)):
            img_path = image_paths[i]
            aud_path = audio_paths[i]
            scene_num = i + 1
            scene_video_name = f"scene_{scene_num}_temp.mp4"
            scene_vid_path = project_dir / scene_video_name
            
            scene_video_paths.append(scene_vid_path)
            scene_video_names.append(scene_video_name)
            
            tasks.append(create_scene_video(img_path, aud_path, scene_vid_path))
            
        logger.info("Generating individual scene video clips in parallel...")
        results = await asyncio.gather(*tasks)
        
        for idx, success in enumerate(results):
            if not success:
                logger.error(f"Failed to generate scene {idx + 1} video clip.")
                raise Exception(f"Video assembly failed at scene {idx + 1}")
                
        # 2. Concatenate individual scene videos
        combined_temp_name = "combined_temp.mp4"
        combined_temp_path = project_dir / combined_temp_name
        
        logger.info("Concatenating scene clips...")
        concat_success = await concatenate_videos(scene_video_names, combined_temp_path)
        if not concat_success:
            logger.error("Failed to concatenate scene videos.")
            raise Exception("Video concatenation failed.")
            
        # 3. Burn subtitles onto combined video
        final_video_path = project_dir / "final_video.mp4"
        logger.info("Burning subtitles onto the combined video...")
        burn_success = await burn_subtitles_to_video(combined_temp_path, srt_path, final_video_path)
        if not burn_success:
            logger.error("Failed to burn subtitles.")
            # Fallback: copy the combined video as final video so the user still gets a video
            try:
                import shutil
                shutil.copy(combined_temp_path, final_video_path)
                logger.warning("Subtitle burning failed. Reverting to video without subtitles.")
            except Exception as e:
                logger.error(f"Failed to copy fallback video: {str(e)}")
                raise Exception("Subtitles burning and fallback video copy failed.")
                
        # 4. Cleanup temporary video files
        logger.info("Cleaning up temporary video assets...")
        for p in scene_video_paths:
            if p.exists():
                try:
                    p.unlink()
                except Exception as e:
                    logger.warning(f"Could not delete temp file {p}: {str(e)}")
                    
        if combined_temp_path.exists():
            try:
                combined_temp_path.unlink()
            except Exception as e:
                logger.warning(f"Could not delete temp combined file: {str(e)}")
                
        logger.info(f"Video assembly successfully finished. Output: {final_video_path}")
        return final_video_path
