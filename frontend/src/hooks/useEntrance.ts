import { useRef } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(useGSAP);

export function useEntrance() {
  const ref = useRef<HTMLDivElement>(null);
  useGSAP(() => {
    if (ref.current) {
      gsap.from(ref.current, {
        opacity: 0,
        y: 24,
        duration: 0.5,
        ease: "power2.out",
      });
    }
  }, { scope: ref });

  return ref;
}

export function useStagger(selector: string, deps: any[] = []) {
  const ref = useRef<HTMLDivElement>(null);
  useGSAP(() => {
    gsap.from(`${selector}`, {
      opacity: 0,
      y: 12,
      stagger: 0.06,
      duration: 0.35,
      ease: "power1.out",
    });
  }, { scope: ref, dependencies: deps });

  return ref;
}
