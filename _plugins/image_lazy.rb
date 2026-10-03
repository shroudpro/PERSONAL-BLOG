# frozen_string_literal: true

# Keep Markdown images from delaying article rendering without generating or
# fetching image placeholders during the build.
Jekyll::Hooks.register [:posts, :documents], :post_render do |doc|
  next unless doc.output_ext == '.html' && doc.output

  doc.output.gsub!(/<img\s+(?![^>]*\bloading=)([^>]+)>/i) do |match|
    if match.match?(/class=["'][^"']*(?:hero-|card-thumb)/i)
      match
    else
      match.sub('<img ', '<img loading="lazy" decoding="async" ')
    end
  end
end
