import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ImageGallery } from "./ImageGallery";
import type { AttachmentResponse } from "../api/types";

vi.mock("../api/endpoints", () => ({
  getOriginalUrl: vi.fn().mockResolvedValue("https://storage.local/original.png"),
}));

const imageAtt = (id: number): AttachmentResponse => ({
  id,
  post_id: 1,
  original_name: `img${id}.png`,
  content_type: "image/png",
  size: 100,
  is_image: true,
  thumbnail_url: `https://storage.local/thumb${id}.jpg`,
});

afterEach(() => vi.clearAllMocks());

describe("ImageGallery (AC6)", () => {
  it("renders a thumbnail card per image attachment", () => {
    render(<ImageGallery attachments={[imageAtt(1), imageAtt(2)]} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });

  it("renders nothing when there are no image attachments", () => {
    const nonImage: AttachmentResponse = {
      id: 9,
      post_id: 1,
      original_name: "doc.txt",
      content_type: "text/plain",
      size: 10,
      is_image: false,
      thumbnail_url: null,
    };
    const { container } = render(<ImageGallery attachments={[nonImage]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("opens the lightbox with the original URL on card click", async () => {
    render(<ImageGallery attachments={[imageAtt(1)]} />);
    fireEvent.click(within(screen.getByRole("listitem")).getByRole("button"));
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
    const dialog = screen.getByRole("dialog");
    const full = within(dialog).getByAltText("img1.png");
    expect(full).toHaveAttribute("src", "https://storage.local/original.png");
  });

  it("closes the lightbox on Escape (FE-AC6-001 a11y)", async () => {
    render(<ImageGallery attachments={[imageAtt(1)]} />);
    fireEvent.click(within(screen.getByRole("listitem")).getByRole("button"));
    await waitFor(() => expect(screen.getByRole("dialog")).toBeInTheDocument());
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });
});
