import type { CSSProperties } from 'react';
import sakuraBranchImage from '@/assets/images/sakura-branch.png';
import './SakuraSway.css';

const PETALS = Array.from({ length: 16 }, (_, index) => ({
  left: (index * 9 + 6) % 100,
  width: 12 + (index % 4) * 4,
  height: Math.round((12 + (index % 4) * 4) * 0.66),
  wideWidth: Math.round((12 + (index % 4) * 4) * 1.18),
  wideHeight: Math.round((12 + (index % 4) * 4) * 0.56),
  delay: -(index * 0.72),
  duration: 9 + (index % 5) * 1.35,
  drift: index % 2 === 0 ? 44 + index * 2 : -36 - index,
  spin: index % 3 === 0 ? 420 : -360,
  opacity: 0.48 + (index % 4) * 0.08,
}));

function SakuraSway() {
  return (
    <div className="sakura-sway" aria-hidden="true">
      <div className="sakura-sway-branch-frame">
        <img
          src={sakuraBranchImage}
          alt=""
          className="sakura-sway-branch"
          draggable={false}
        />
      </div>

      <div className="sakura-sway-petals">
        {PETALS.map((petal, index) => (
          <span
            key={index}
            className="sakura-sway-petal"
            style={{
              '--sakura-left': `${petal.left}%`,
              '--sakura-width': `${petal.width}px`,
              '--sakura-height': `${petal.height}px`,
              '--sakura-wide-width': `${petal.wideWidth}px`,
              '--sakura-wide-height': `${petal.wideHeight}px`,
              '--sakura-delay': `${petal.delay}s`,
              '--sakura-duration': `${petal.duration}s`,
              '--sakura-drift': `${petal.drift}px`,
              '--sakura-mid-drift': `${Math.round(petal.drift * 0.55)}px`,
              '--sakura-spin': `${petal.spin}deg`,
              '--sakura-mid-spin': `${Math.round(petal.spin * 0.58)}deg`,
              '--sakura-opacity': petal.opacity,
            } as CSSProperties}
          />
        ))}
      </div>
    </div>
  );
}

export default SakuraSway;
