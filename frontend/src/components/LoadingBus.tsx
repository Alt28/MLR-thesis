import busSprite from '../assets/loading-bus.svg'

/** Decorative motion only; the parent loading status announces actual work. */
export function LoadingBus() {
  return <div className="bus-loader" data-motion="on">
    <div className="loading-bus-scene" aria-hidden="true">
      <div className="bus-speed-lines"><i/><i/><i/></div>
      <div className="bus-travel">
        <div className="bus-sprite"><img src={busSprite} alt="" width="160" height="130"/><span className="bus-wheel"/><span className="bus-wheel rear"/></div>
        <div className="bus-shadow"/>
      </div>
      <div className="bus-road"><span/></div>
    </div>
  </div>
}
