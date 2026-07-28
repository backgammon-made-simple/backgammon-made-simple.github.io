```{=html}
<%
const asList = (value) => {
  if (Array.isArray(value)) return value;
  if (value === undefined || value === null || value === "") return [];
  return [value];
};
%>

<div class="bms-learn-list list" data-bms-learn-list>
<% for (const item of items) {
  const difficulties = asList(item.categories);
  const tracks = asList(item.tags);
%>
  <article
    class="bms-learn-lesson-card"
    <%= metadataAttrs(item) %>
    data-bms-learn-item
    data-bms-difficulties='<%- JSON.stringify(difficulties) %>'
    data-bms-tracks='<%- JSON.stringify(tracks) %>'>

    <h3 class="listing-title bms-learn-lesson-title">
      <span class="bms-cube-lesson-number" aria-hidden="true"></span>
      <a href="<%- item.path %>"><%- item.title %></a>
    </h3>

    <% if (item.description) { %>
      <p class="listing-description bms-learn-lesson-description"><%- item.description %></p>
    <% } %>

    <p class="bms-learn-lesson-action"><a href="<%- item.path %>">Open lesson</a></p>
  </article>
<% } %>
</div>
```
