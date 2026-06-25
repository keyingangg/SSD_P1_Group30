-- Run in the Supabase SQL editor for this project.
--
-- The backend authenticates to Storage using the anon key (NFSR-AZ-06: the
-- service_role key must never be used in the application backend, since it
-- bypasses RLS entirely). These policies grant the anon role only the
-- minimum access needed for the upload/signed-URL flow, scoped to the
-- auction-images bucket (NFSR-C-02).
--
-- storage.objects has RLS enabled by default on every Supabase project.

CREATE POLICY "auction_images_anon_insert"
ON storage.objects
FOR INSERT
TO anon
WITH CHECK (bucket_id = 'auction-images');

CREATE POLICY "auction_images_anon_select"
ON storage.objects
FOR SELECT
TO anon
USING (bucket_id = 'auction-images');
