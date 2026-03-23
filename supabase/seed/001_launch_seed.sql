insert into public.credit_packs (name, credits, price_cents, stripe_price_id)
values
  ('Starter', 50, 2900, 'price_starter'),
  ('Pro', 150, 6900, 'price_pro'),
  ('Agency', 500, 17900, 'price_agency'),
  ('Enterprise', 2000, 49900, 'price_enterprise')
on conflict (stripe_price_id) do update
set
  name = excluded.name,
  credits = excluded.credits,
  price_cents = excluded.price_cents,
  active = true;

insert into public.media_presets (slug, name, description, style_prompt)
values
  ('DEFAULT', 'Default', 'Balanced launch preset', 'cinematic, high quality'),
  ('GHIBLI', 'Ghibli Studio', 'Soft anime watercolor look', 'Studio Ghibli anime art style, watercolor, hand-drawn'),
  ('PIXAR', 'Pixar', 'Bright stylized 3D look', 'Pixar 3D animation style, vibrant colors'),
  ('ANIME', 'Anime', 'Sharp cel-shaded anime look', 'Japanese anime style, sharp lines'),
  ('EDUCATIONAL', 'Educational', 'Infographic-forward educational look', 'Clean, infographic style, diagrams'),
  ('REALIST', 'Realist', 'Photoreal documentary look', 'Photorealistic, documentary style')
on conflict (slug) do update
set
  name = excluded.name,
  description = excluded.description,
  style_prompt = excluded.style_prompt,
  active = true;

insert into public.caption_presets (name, font_family, font_size, color, background_color, animation, position)
values
  ('Wrap 1', 'Space Grotesk', 48, '#FFFFFF', 'rgba(15,23,42,0.78)', 'word-by-word', 'bottom')
on conflict (name) do update
set
  font_family = excluded.font_family,
  font_size = excluded.font_size,
  color = excluded.color,
  background_color = excluded.background_color,
  animation = excluded.animation,
  position = excluded.position;

insert into public.music_tracks (name, url, duration_seconds, genre, mood, active)
values
  ('Observer', 'https://example.com/audio/observer.mp3', 32, 'ambient', 'focused', true)
on conflict (name) do update
set
  url = excluded.url,
  duration_seconds = excluded.duration_seconds,
  genre = excluded.genre,
  mood = excluded.mood,
  active = excluded.active;
