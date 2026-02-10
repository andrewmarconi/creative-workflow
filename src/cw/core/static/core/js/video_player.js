/**
 * Alpine.js component for video player with scene timeline markers.
 * Displays video with interactive scene navigation.
 */
function videoPlayer(videoUrl, scenes) {
  return {
    videoUrl: videoUrl,
    scenes: scenes || [],
    currentTime: 0,
    duration: 0,
    currentScene: -1,
    currentProgress: 0,

    onVideoLoaded() {
      this.duration = this.$refs.videoPlayer.duration;
    },

    onTimeUpdate() {
      this.currentTime = this.$refs.videoPlayer.currentTime;
      this.currentProgress = (this.currentTime / this.duration) * 100;

      // Update current scene
      this.currentScene = this.scenes.findIndex((scene, index) => {
        const nextScene = this.scenes[index + 1];
        return this.currentTime >= scene.start_time &&
               (!nextScene || this.currentTime < nextScene.start_time);
      });
    },

    seekToScene(scene) {
      this.$refs.videoPlayer.currentTime = scene.start_time;
      this.$refs.videoPlayer.play();
    },

    getScenePosition(scene) {
      if (!this.duration) return 0;
      return (scene.start_time / this.duration) * 100;
    },

    formatTime(seconds) {
      const mins = Math.floor(seconds / 60);
      const secs = Math.floor(seconds % 60);
      return `${mins}:${secs.toString().padStart(2, '0')}`;
    },
  };
}
