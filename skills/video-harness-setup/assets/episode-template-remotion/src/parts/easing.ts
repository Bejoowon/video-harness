import { Easing } from "remotion";

/**
 * theme.ts의 motion.inEase/outEase는 GSAP 스타일 이름("power3.out" 등)이다.
 * Remotion에는 그 이름이 없으므로 Remotion의 Easing 함수로 변환한다.
 *
 * power1~4 는 각각 poly(2)~poly(5)에 대응한다(Quad/Cubic/Quart/Quint).
 * ".in" / ".out" / ".inOut" 접미사는 Easing.in/out/inOut로 감싼다.
 * "none"과 "linear"는 Easing.linear로 매핑한다.
 * 그 외 알 수 없는 이름은 Easing.out(Easing.cubic)으로 대체한다.
 */

const POWER_DEGREE: Record<string, number> = {
  power1: 2,
  power2: 3,
  power3: 4,
  power4: 5,
};

export function toEasing(name: string): (input: number) => number {
  if (name === "none" || name === "linear") {
    return Easing.linear;
  }

  const match = /^(power[1-4])\.(in|out|inOut)$/.exec(name);
  if (match) {
    const [, power, direction] = match;
    const base = Easing.poly(POWER_DEGREE[power]);
    if (direction === "in") return Easing.in(base);
    if (direction === "out") return Easing.out(base);
    return Easing.inOut(base);
  }

  return Easing.out(Easing.cubic);
}
