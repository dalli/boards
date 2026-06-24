import { useEffect, useRef, useState } from "react";
import * as api from "../api/endpoints";
import type { AttachmentResponse } from "../api/types";

// AC6: thumbnail card grid → click → lightbox showing the original (presigned GET fetched
// on demand). Only image attachments render in the grid.
export function ImageGallery({ attachments }: { attachments: AttachmentResponse[] }) {
  const images = attachments.filter((a) => a.is_image && a.thumbnail_url);
  const [lightbox, setLightbox] = useState<{ url: string; name: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  // FE-AC6-001: when the lightbox opens, move focus into it and close on Escape; the dialog
  // is a single focusable control, so Escape + focus-on-open is sufficient for a basic trap.
  useEffect(() => {
    if (!lightbox) return;
    closeButtonRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setLightbox(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [lightbox]);

  if (images.length === 0) return null;

  const openOriginal = async (att: AttachmentResponse) => {
    setError(null);
    try {
      const url = await api.getOriginalUrl(att.id);
      setLightbox({ url, name: att.original_name });
    } catch {
      setError("원본 이미지를 불러오지 못했습니다.");
    }
  };

  return (
    <div className="image-gallery">
      <ul className="thumbnail-grid">
        {images.map((att) => (
          <li key={att.id} className="thumbnail-card">
            <button
              type="button"
              onClick={() => openOriginal(att)}
              aria-label={`이미지 크게 보기: ${att.original_name}`}
            >
              <img src={att.thumbnail_url ?? undefined} alt={att.original_name} loading="lazy" />
            </button>
          </li>
        ))}
      </ul>
      {error && <p className="error">{error}</p>}
      {lightbox && (
        <div
          className="lightbox"
          role="dialog"
          aria-modal="true"
          aria-label="원본 이미지 보기"
          onClick={() => setLightbox(null)}
        >
          <img src={lightbox.url} alt={lightbox.name} />
          <button
            ref={closeButtonRef}
            className="lightbox-close"
            onClick={() => setLightbox(null)}
            aria-label="닫기"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}
