```{=html}
<%
const asList = (value) => {
  if (Array.isArray(value)) return value;
  if (value === undefined || value === null || value === "") return [];
  return [value];
};

const formatReadingTime = (value) => {
  if (value === undefined || value === null || value === "") return "";
  const text = String(value).trim();
  if (/\bread$/i.test(text)) return text;
  if (/\bmin$/i.test(text)) return `${text} read`;
  if (/^\d+$/.test(text)) return `${text} min read`;
  return text;
};
%>

<div class="bms-research-list list" data-bms-research-list>
<% for (const item of items) {
  const categories = asList(item.categories);
  const tags = asList(item.tags);
  const readingTime = formatReadingTime(item["reading-time"]);
%>
  <article
    class="bms-research-post"
    <%= metadataAttrs(item) %>
    data-bms-research-item
    data-bms-categories='<%- JSON.stringify(categories) %>'
    data-bms-tags='<%- JSON.stringify(tags) %>'>

    <div class="bms-research-post-header">
      <div>
        <h2 class="listing-title bms-research-post-title">
          <a href="<%- item.path %>"><%- item.title %></a>
        </h2>
        <% if (item.subtitle) { %>
          <p class="listing-subtitle bms-research-post-subtitle"><%- item.subtitle %></p>
        <% } %>
      </div>

      <% if (readingTime) { %>
        <p class="listing-reading-time bms-research-post-time"><%- readingTime %></p>
      <% } %>
    </div>

    <% if (item.description) { %>
      <p class="listing-description bms-research-post-description"><%- item.description %></p>
    <% } %>

    <% if (categories.length || tags.length) { %>
      <div class="bms-research-post-taxonomy">
        <% if (categories.length) { %>
          <div class="bms-research-post-taxonomy-group" aria-label="Article categories">
            <% for (const category of categories) { %>
              <button
                type="button"
                class="bms-research-card-taxonomy bms-research-card-taxonomy--category"
                data-bms-card-category="<%- category %>">
                <%- category %>
              </button>
            <% } %>
          </div>
        <% } %>

        <% if (tags.length) { %>
          <div class="bms-research-post-taxonomy-group" aria-label="Article tags">
            <% for (const tag of tags) { %>
              <button
                type="button"
                class="bms-research-card-taxonomy bms-research-card-taxonomy--tag"
                data-bms-card-tag="<%- tag %>">
                <%- tag %>
              </button>
            <% } %>
          </div>
        <% } %>
      </div>
    <% } %>

    <p class="bms-research-post-action">
      <a href="<%- item.path %>">Read article</a>
    </p>
  </article>
<% } %>
</div>
```