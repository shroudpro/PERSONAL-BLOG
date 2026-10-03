# frozen_string_literal: true

# Convert ||spoiler|| Markdown syntax into accessible, theme-styled markup.
Jekyll::Hooks.register [:posts, :pages, :documents], :pre_render do |doc|
  content = doc.content
  next unless content&.include?('||')

  code_blocks = []
  content.gsub!(/(`+)(.+?)\1/m) do |match|
    code_blocks << match
    "__SPOILER_CODE_#{code_blocks.length - 1}__"
  end

  html_blocks = []
  content.gsub!(/<(pre|code)[^>]*>.*?<\/\1>/mi) do |match|
    html_blocks << match
    "__SPOILER_HTML_#{html_blocks.length - 1}__"
  end

  content.gsub!(/(?<!\|)\|\|(?!\|)(.+?)(?<!\|)\|\|(?!\|)/m) do
    inner = Regexp.last_match(1)
    "<span class=\"markdown-spoiler\" data-spoiler=\"true\" tabindex=\"0\" role=\"button\" aria-expanded=\"false\" title=\"点击显示隐藏内容\"><span class=\"markdown-spoiler-inner\" markdown=\"span\">#{inner}</span></span>"
  end

  content.gsub!(/__SPOILER_HTML_(\d+)__/) { html_blocks[Regexp.last_match(1).to_i] }
  content.gsub!(/__SPOILER_CODE_(\d+)__/) { code_blocks[Regexp.last_match(1).to_i] }

  doc.content = content
end
