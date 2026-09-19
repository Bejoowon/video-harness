import React from "react";
import { theme } from "../theme";

export type SourceLabelProps = {
  text: string;
};

export const SourceLabel: React.FC<SourceLabelProps> = ({ text }) => {
  return (
    <div
      style={{
        position: "absolute",
        right: theme.layout.safeSide,
        bottom: theme.layout.sourceBottom,
      }}
    >
      <p
        style={{
          margin: 0,
          fontFamily: `${theme.typography.noteFamily}, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif`,
          fontWeight: theme.typography.noteWeight,
          fontSize: theme.typography.noteSize,
          color: theme.colors.fg,
          opacity: 0.8,
        }}
      >
        {text}
      </p>
    </div>
  );
};
