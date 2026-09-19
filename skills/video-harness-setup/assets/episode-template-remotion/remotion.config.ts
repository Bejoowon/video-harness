/**
 * Node.js API로 렌더할 때는 이 설정 파일이 적용되지 않는다. 그때는 옵션을
 * API 호출에 직접 넘긴다. 전체 옵션: https://remotion.dev/docs/config
 */

import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
