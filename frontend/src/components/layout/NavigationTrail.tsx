import { Link, useRouter } from "../../app/router";
import type { BreadcrumbItem } from "../../utils/navigation";

type NavigationTrailProps = {
  backFallback: string;
  breadcrumbs: BreadcrumbItem[];
};

export const NavigationTrail = ({ backFallback, breadcrumbs }: NavigationTrailProps) => {
  const { back } = useRouter();

  return (
    <div className="navigation-trail" aria-label="Navegacion contextual">
      <button className="back-button" type="button" onClick={() => back(backFallback)}>
        Volver
      </button>
      <nav className="breadcrumbs" aria-label="Ruta actual">
        {breadcrumbs.map((item, index) => {
          const isCurrent = index === breadcrumbs.length - 1;
          return isCurrent ? (
            <span aria-current="page" key={item.href}>
              {item.label}
            </span>
          ) : (
            <Link href={item.href} key={item.href}>
              {item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
};
