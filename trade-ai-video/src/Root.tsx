import { Composition } from "remotion";
import { TradeAIVideo } from "./TradeAIVideo";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="TradeAIVideo"
        component={TradeAIVideo}
        durationInFrames={900}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
