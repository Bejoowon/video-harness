export const theme = {
  colors: {
    bg: "#101318",
    fg: "#FFFFFF",
    accent: "#FFE14D",
  },
  typography: {
    captionFamily: "Pretendard",
    captionWeight: 700,
    captionSize: 80,
    titleFamily: "Paperlogy",
    titleWeight: 900,
    titleSize: 96,
    noteFamily: "Pretendard",
    noteWeight: 500,
    noteSize: 40,
  },
  layout: {
    titleTop: 140,
    captionBottom: 420,
    sourceBottom: 96,
    safeSide: 72,
  },
  stroke: {
    captionOutline: 10,
    shadow: "0 6px 0 rgba(0,0,0,0.35)",
  },
  motion: {
    inDuration: 0.35,
    inEase: "power3.out",
    outDuration: 0.2,
    outEase: "power1.in",
    stagger: 0.06,
  },
  canvas: {
    width: 1080,
    height: 1920,
    fps: 30,
  },
} as const;
