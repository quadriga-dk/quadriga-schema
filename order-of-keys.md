# Order of Keys in the JSON-Schema files

1. `$id`
2. Type information (`type`) (with format (`format`), if applicable)
3. Description
4. `@id` if it exists
5. `required` and `additionalProperties` if applicable
6. Keys describing the content like `items` or `properties`
