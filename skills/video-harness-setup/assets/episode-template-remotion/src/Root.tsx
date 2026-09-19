import React from "react";
import { CalculateMetadataFunction, Composition } from "remotion";
import { Episode, EpisodeProps } from "./Episode";
import { theme } from "./theme";

const DEFAULT_DURATION_SECONDS = 10;

const calculateEpisodeMetadata: CalculateMetadataFunction<EpisodeProps> = ({
  props,
}) => {
  return {
    durationInFrames: Math.round(props.durationInSeconds * theme.canvas.fps),
    fps: theme.canvas.fps,
    width: theme.canvas.width,
    height: theme.canvas.height,
  };
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Episode"
      component={Episode}
      fps={theme.canvas.fps}
      width={theme.canvas.width}
      height={theme.canvas.height}
      durationInFrames={theme.canvas.fps * DEFAULT_DURATION_SECONDS}
      defaultProps={{
        title: "제목이 들어갑니다",
        caption: "자막 한 줄이 들어갑니다",
        source: "출처 표기",
        narration: null,
        durationInSeconds: DEFAULT_DURATION_SECONDS,
      }}
      calculateMetadata={calculateEpisodeMetadata}
    />
  );
};
