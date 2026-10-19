import { ShieldCheck } from "lucide-react";
import "../styles/banner.css";

function Banner({ icon: Icon = ShieldCheck, title, children }) {
  return (
    <div className="banner" role="note">
      <span className="banner__icon">
        <Icon size={20} aria-hidden="true" />
      </span>

      <p className="banner__text">
        <strong className="banner__title body-semibold">{title}</strong>
        <span className="banner__separator" aria-hidden="true">
          ·
        </span>
        <span className="banner__body caption-rg">{children}</span>
      </p>
    </div>
  );
}

export default Banner;
